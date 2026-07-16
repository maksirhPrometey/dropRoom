import logging
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from src.catalog.models import Brand, Category, Color, Product, ProductImage, ProductVariant
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.parser import parse_caption
from src.telegram_import.services.parser_types import ParsedVariant
from src.telegram_import.services.photo_utils import normalize_product_image, rank_photo_files
from src.telegram_import.services.telegram_api import TelegramAPIError, download_photo

logger = logging.getLogger("src.telegram_import")


class ImportError(Exception):
    pass


def _default_brand() -> Brand | None:
    """Лише явний TELEGRAM_DEFAULT_BRAND_ID з .env. Без fallback на «перший у БД»."""
    brand_id = settings.TELEGRAM_DEFAULT_BRAND_ID
    if not brand_id:
        return None
    return Brand.objects.filter(pk=brand_id, is_active=True).first()


def _default_category() -> Category | None:
    """Лише явний TELEGRAM_DEFAULT_CATEGORY_ID з .env. Без fallback на першу категорію."""
    category_id = settings.TELEGRAM_DEFAULT_CATEGORY_ID
    if not category_id:
        return None
    return Category.objects.filter(pk=category_id).first()


def _get_or_create_color(name: str | None) -> Color | None:
    if not name:
        return None
    slug_base = slugify(name) or "color"
    slug = slug_base
    counter = 1
    while Color.objects.filter(slug=slug).exclude(name=name).exists():
        slug = f"{slug_base}-{counter}"
        counter += 1
    color, _ = Color.objects.get_or_create(
        name=name[:80],
        defaults={"slug": slug, "hex_code": "#cccccc"},
    )
    return color


def _upsert_import_record(
    *,
    channel_id: int,
    message_id: int,
    media_group_id: str,
    caption: str,
    photo_file_ids: list[str],
) -> TelegramImport:
    record, created = TelegramImport.objects.get_or_create(
        channel_id=channel_id,
        message_id=message_id,
        defaults={
            "media_group_id": media_group_id,
            "raw_caption": caption,
            "photo_file_ids": photo_file_ids,
        },
    )
    if created:
        return record

    changed = False
    if media_group_id and record.media_group_id != media_group_id:
        record.media_group_id = media_group_id
        changed = True
    if caption and record.raw_caption != caption:
        record.raw_caption = caption
        changed = True
        if record.status == TelegramImport.STATUS_IMPORTED:
            record.status = TelegramImport.STATUS_PENDING
    merged_ids = list(dict.fromkeys([*record.photo_file_ids, *photo_file_ids]))
    if merged_ids != record.photo_file_ids:
        record.photo_file_ids = merged_ids
        changed = True
    if changed:
        record.save(
            update_fields=[
                "media_group_id",
                "raw_caption",
                "photo_file_ids",
                "status",
                "updated_at",
            ]
        )
    return record


def _find_group_leader(
    channel_id: int,
    media_group_id: str,
    caption: str,
) -> TelegramImport | None:
    if not media_group_id:
        return None
    qs = TelegramImport.objects.filter(
        channel_id=channel_id,
        media_group_id=media_group_id,
    ).order_by("message_id")
    if not caption:
        leader = qs.filter(product_id__isnull=False).order_by("message_id").first()
        if leader:
            return leader
        return qs.exclude(raw_caption="").first()
    return qs.filter(raw_caption=caption).first() or qs.first()


def _collect_group_photo_file_ids(channel_id: int, media_group_id: str) -> list[str]:
    if not media_group_id:
        return []

    merged: list[str] = []
    records = TelegramImport.objects.filter(
        channel_id=channel_id,
        media_group_id=media_group_id,
    ).order_by("message_id")
    for group_record in records:
        for file_id in group_record.photo_file_ids:
            if file_id and file_id not in merged:
                merged.append(file_id)
    return merged


def _sync_group_images(
    product: Product,
    *,
    channel_id: int,
    media_group_id: str,
    alt_text: str,
) -> None:
    file_ids = _collect_group_photo_file_ids(channel_id, media_group_id)
    if not file_ids:
        return

    stub = TelegramImport(photo_file_ids=file_ids)
    _sync_images(product, stub, alt_text)


def _attach_pending_group_records(
    *,
    channel_id: int,
    media_group_id: str,
    product: Product,
    imported_at,
) -> None:
    if not media_group_id:
        return

    TelegramImport.objects.filter(
        channel_id=channel_id,
        media_group_id=media_group_id,
        product__isnull=True,
    ).update(
        product=product,
        status=TelegramImport.STATUS_IMPORTED,
        imported_at=imported_at,
        error="",
    )


def _attach_record_to_group_product(
    record: TelegramImport,
    *,
    leader: TelegramImport,
    channel_id: int,
    media_group_id: str,
) -> None:
    product = leader.product
    if not product:
        return

    record.product = product
    record.status = TelegramImport.STATUS_IMPORTED
    record.imported_at = leader.imported_at or timezone.now()
    record.error = ""
    record.save(
        update_fields=["status", "product", "imported_at", "error", "updated_at"]
    )
    _sync_group_images(
        product,
        channel_id=channel_id,
        media_group_id=media_group_id,
        alt_text=product.name,
    )


def _build_variant_sku(
    *,
    channel_id: int,
    message_id: int,
    color_slug: str,
    size: str,
    index: int,
    used: set[str],
) -> str:
    size_slug = slugify(size) or f"size-{index}"
    channel_key = abs(int(channel_id))
    candidates = [
        f"TG-{channel_key}-{message_id}-{color_slug}-{size_slug}",
        f"TG-{channel_key}-{message_id}-{index}-{size_slug}",
        f"TG-{channel_key}-{message_id}-{index}-{size_slug}-{len(used) + 1}",
    ]
    for candidate in candidates:
        sku = candidate[:64]
        if sku not in used:
            return sku
    return f"TG-{channel_key}-{message_id}-{index}-{len(used)}"[:64]


def _find_existing_variant(
    product: Product,
    *,
    size: str,
    color,
    sku: str,
) -> ProductVariant | None:
    obj = ProductVariant.objects.filter(
        product=product, size=size, color=color
    ).first()
    if obj:
        return obj
    # Null-color match лише коли новий варіант теж без кольору —
    # інакше кілька ONE SIZE з різними кольорами зливаються в один.
    if color is None:
        obj = (
            ProductVariant.objects.filter(
                product=product, size=size, color__isnull=True
            )
            .order_by("pk")
            .first()
        )
        if obj:
            return obj
    by_sku = ProductVariant.objects.filter(sku=sku).first()
    if by_sku and by_sku.product_id == product.pk:
        # Не перевикористовувати SKU іншого кольору
        if (by_sku.color_id is None) == (color is None) and (
            color is None or by_sku.color_id == color.pk
        ):
            return by_sku
    return None


def _compute_compare_price(
    parsed_variants: list[ParsedVariant], base_price: Decimal
) -> Decimal | None:
    """Стара ціна, прив'язана саме до варіанта з `base_price` (мін. ціна
    серед variants) — щоб закреслена ціна на сайті відповідала саме тій
    сумі знижки, яку продавець вказав у Telegram."""
    for variant in parsed_variants:
        if (
            variant.price == base_price
            and variant.compare_price
            and variant.compare_price > base_price
        ):
            return variant.compare_price
    return None


def _sync_variants(
    product: Product,
    *,
    channel_id: int,
    message_id: int,
    parsed_variants,
    default_price: Decimal,
) -> None:
    if not parsed_variants:
        parsed_variants = [
            ParsedVariant(
                size=settings.TELEGRAM_DEFAULT_SIZE,
                price=default_price,
                stock_qty=settings.TELEGRAM_DEFAULT_STOCK,
                is_available=True,
            )
        ]

    used_skus: set[str] = set(
        ProductVariant.objects.exclude(product=product).values_list("sku", flat=True)
    )
    keep_ids: list[int] = []
    for index, variant in enumerate(parsed_variants, start=1):
        color = _get_or_create_color(variant.color)
        size = variant.size[:20]
        color_slug = slugify(variant.color or "default") or "default"
        sku = _build_variant_sku(
            channel_id=channel_id,
            message_id=message_id,
            color_slug=color_slug,
            size=size,
            index=index,
            used=used_skus,
        )
        obj = _find_existing_variant(product, size=size, color=color, sku=sku)

        if obj is None:
            obj = ProductVariant(product=product)

        obj.size = size
        obj.color = color
        # Якщо обраний SKU зайнятий іншим варіантом — згенерувати вільний.
        if (
            ProductVariant.objects.filter(sku=sku)
            .exclude(pk=obj.pk or 0)
            .exists()
        ):
            used_skus.add(sku)
            sku = _build_variant_sku(
                channel_id=channel_id,
                message_id=message_id,
                color_slug=color_slug,
                size=size,
                index=index,
                used=used_skus,
            )
        obj.sku = sku
        obj.price = variant.price if variant.price and variant.price > 0 else default_price
        obj.stock_qty = variant.stock_qty
        obj.is_available = variant.is_available
        obj.save()
        used_skus.add(sku)
        keep_ids.append(obj.pk)

    if keep_ids:
        product.variants.exclude(pk__in=keep_ids).delete()

    prices = [
        variant.price
        for variant in parsed_variants
        if variant.price is not None
        and variant.price > 0
        and variant.is_available
    ]
    if not prices:
        prices = [
            variant.price
            for variant in parsed_variants
            if variant.price is not None and variant.price > 0
        ]
    if prices:
        product.base_price = min(prices)
        product.compare_price = _compute_compare_price(
            parsed_variants, product.base_price
        )
        product.save(update_fields=["base_price", "compare_price"])


def _find_duplicate_product(
    channel_id: int,
    message_id: int,
    caption: str,
) -> Product | None:
    normalized = caption.strip()
    if not normalized:
        return None
    existing = (
        TelegramImport.objects.filter(
            channel_id=channel_id,
            raw_caption=normalized,
            product_id__isnull=False,
            status=TelegramImport.STATUS_IMPORTED,
        )
        .exclude(message_id=message_id)
        .select_related("product")
        .order_by("message_id")
        .first()
    )
    return existing.product if existing else None


def _sync_images(
    product: Product,
    record: TelegramImport,
    alt_text: str,
    photo_files: list[tuple[str, bytes]] | None = None,
    *,
    merge_existing: bool = False,
) -> None:
    existing_count = product.images.count()

    if photo_files:
        combined = list(photo_files)
        if merge_existing and product.images.exists():
            for image in product.images.order_by("sort_order"):
                if not image.image:
                    continue
                with image.image.open("rb") as handle:
                    combined.append((image.image.name.rsplit("/", 1)[-1], handle.read()))

        combined = rank_photo_files(combined)
        if not combined:
            return

        product.images.all().delete()
        for sort_order, (filename, content) in enumerate(combined):
            ProductImage.objects.create(
                product=product,
                image=ContentFile(
                    normalize_product_image(content),
                    name=filename,
                ),
                alt=alt_text,
                is_primary=(sort_order == 0),
                sort_order=sort_order,
            )
        return

    for sort_order, file_id in enumerate(record.photo_file_ids):
        if product.images.filter(image__icontains=file_id).exists():
            continue
        try:
            photo = download_photo(file_id)
        except (TelegramAPIError, OSError) as exc:
            logger.warning("Не вдалося завантажити фото %s: %s", file_id, exc)
            continue
        ProductImage.objects.create(
            product=product,
            image=ContentFile(photo.content, name=photo.filename),
            alt=alt_text,
            is_primary=(existing_count == 0 and sort_order == 0),
            sort_order=existing_count + sort_order,
        )


def import_telegram_message(
    *,
    channel_id: int,
    message_id: int,
    caption: str,
    photo_file_ids: list[str],
    media_group_id: str = "",
    photo_files: list[tuple[str, bytes]] | None = None,
) -> TelegramImport:
    allowed_channel_ids = settings.TELEGRAM_ALLOWED_CHANNEL_IDS
    if allowed_channel_ids and channel_id not in allowed_channel_ids:
        record, _created = TelegramImport.objects.get_or_create(
            channel_id=channel_id,
            message_id=message_id,
            defaults={
                "media_group_id": media_group_id,
                "raw_caption": caption,
                "photo_file_ids": photo_file_ids,
                "status": TelegramImport.STATUS_SKIPPED,
                "error": "Канал не в whitelist",
            },
        )
        return record

    record = _upsert_import_record(
        channel_id=channel_id,
        message_id=message_id,
        media_group_id=media_group_id,
        caption=caption,
        photo_file_ids=photo_file_ids,
    )

    if media_group_id and not caption.strip():
        leader = _find_group_leader(channel_id, media_group_id, caption)
        if leader and leader.pk != record.pk and leader.product_id:
            _attach_record_to_group_product(
                record,
                leader=leader,
                channel_id=channel_id,
                media_group_id=media_group_id,
            )
            return record

        record.status = TelegramImport.STATUS_PENDING
        record.error = "Очікує лідер-пост альбому"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    if not photo_file_ids and not photo_files and not caption.strip():
        record.status = TelegramImport.STATUS_SKIPPED
        record.error = "Порожнє повідомлення"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    if photo_files:
        ranked_photos = rank_photo_files(photo_files)
        if not ranked_photos and not photo_file_ids:
            record.status = TelegramImport.STATUS_SKIPPED
            record.error = "Лише скріншоти або службові зображення"
            record.save(update_fields=["status", "error", "updated_at"])
            return record
        photo_files = ranked_photos
    if not photo_files and not photo_file_ids and not caption.strip():
        record.status = TelegramImport.STATUS_SKIPPED
        record.error = "Немає придатного фото"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    if not caption.strip() and not media_group_id:
        record.status = TelegramImport.STATUS_SKIPPED
        record.error = "Фото без опису"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    default_brand = _default_brand()
    default_category = _default_category()

    parsed = parse_caption(
        caption or record.raw_caption,
        default_brand=default_brand,
        default_category=default_category,
        default_gender=settings.TELEGRAM_DEFAULT_GENDER,
    )

    if not parsed.brand:
        record.status = TelegramImport.STATUS_FAILED
        record.error = "Не вдалося визначити бренд з caption"
        record.save(update_fields=["status", "error", "updated_at"])
        raise ImportError(record.error)

    if not parsed.category:
        record.status = TelegramImport.STATUS_FAILED
        record.error = "Не вдалося визначити категорію з caption"
        record.save(update_fields=["status", "error", "updated_at"])
        raise ImportError(record.error)

    caption_text = (caption or record.raw_caption).strip()
    duplicate_product = _find_duplicate_product(channel_id, message_id, caption_text)

    default_price = Decimal(settings.TELEGRAM_DEFAULT_PRICE)
    base_price = parsed.base_price or default_price
    compare_price = parsed.compare_price

    # Атомарний блок лише навколо самого запису товару: якщо тут щось
    # впаде, не хочемо ні напів-створеного Product, ні втраченого
    # запису про помилку (record.save() вище вже поза цим блоком).
    with transaction.atomic():
        product = record.product or duplicate_product
        if not product:
            product = Product.objects.create(
                brand=parsed.brand,
                category=parsed.category,
                name=parsed.name,
                description=parsed.description,
                gender=parsed.gender,
                base_price=base_price,
                compare_price=compare_price,
                is_active=settings.TELEGRAM_IMPORT_AS_ACTIVE,
            )
            record.product = product
        else:
            record.product = product
            product.brand = parsed.brand
            product.category = parsed.category
            product.name = parsed.name
            product.description = parsed.description
            product.gender = parsed.gender
            product.base_price = base_price
            product.compare_price = compare_price
            product.save()

        _sync_variants(
            product,
            channel_id=channel_id,
            message_id=message_id,
            parsed_variants=parsed.variants,
            default_price=default_price,
        )
        _sync_images(
            product,
            record,
            parsed.name,
            photo_files=photo_files,
            merge_existing=bool(duplicate_product and photo_files),
        )

    record.status = TelegramImport.STATUS_IMPORTED
    record.imported_at = timezone.now()
    record.error = ""
    record.save(
        update_fields=[
            "product",
            "status",
            "imported_at",
            "error",
            "updated_at",
        ]
    )

    if media_group_id:
        _sync_group_images(
            product,
            channel_id=channel_id,
            media_group_id=media_group_id,
            alt_text=parsed.name,
        )
        _attach_pending_group_records(
            channel_id=channel_id,
            media_group_id=media_group_id,
            product=product,
            imported_at=record.imported_at,
        )

    logger.info("Імпортовано товар %s з TG %s/%s", product.pk, channel_id, message_id)
    return record
