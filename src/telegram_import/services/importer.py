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
    brand_id = settings.TELEGRAM_DEFAULT_BRAND_ID
    if not brand_id:
        return Brand.objects.filter(is_active=True).order_by("id").first()
    return Brand.objects.filter(pk=brand_id, is_active=True).first()


def _default_category() -> Category | None:
    category_id = settings.TELEGRAM_DEFAULT_CATEGORY_ID
    if not category_id:
        return Category.objects.order_by("sort_order", "id").first()
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
        return qs.exclude(raw_caption="").first()
    return qs.filter(raw_caption=caption).first() or qs.first()


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

    seen_skus: set[str] = set()
    for index, variant in enumerate(parsed_variants, start=1):
        color = _get_or_create_color(variant.color)
        color_slug = slugify(variant.color or "default") or "default"
        sku = f"TG-{channel_id}-{message_id}-{color_slug}-{variant.size}"[:64]
        if sku in seen_skus:
            sku = f"TG-{channel_id}-{message_id}-{index}"[:64]
        seen_skus.add(sku)

        ProductVariant.objects.update_or_create(
            product=product,
            size=variant.size[:20],
            color=color,
            defaults={
                "sku": sku,
                "price": variant.price,
                "stock_qty": variant.stock_qty,
                "is_available": variant.is_available,
            },
        )


def _sync_images(
    product: Product,
    record: TelegramImport,
    alt_text: str,
    photo_files: list[tuple[str, bytes]] | None = None,
) -> None:
    existing_count = product.images.count()

    if photo_files:
        photo_files = rank_photo_files(photo_files)
        if not photo_files:
            return

        product.images.all().delete()
        for sort_order, (filename, content) in enumerate(photo_files):
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


@transaction.atomic
def import_telegram_message(
    *,
    channel_id: int,
    message_id: int,
    caption: str,
    photo_file_ids: list[str],
    media_group_id: str = "",
    photo_files: list[tuple[str, bytes]] | None = None,
) -> TelegramImport:
    if settings.TELEGRAM_CHANNEL_ID and channel_id != settings.TELEGRAM_CHANNEL_ID:
        record = TelegramImport.objects.create(
            channel_id=channel_id,
            message_id=message_id,
            media_group_id=media_group_id,
            raw_caption=caption,
            photo_file_ids=photo_file_ids,
            status=TelegramImport.STATUS_SKIPPED,
            error="Канал не в whitelist",
        )
        return record

    record = _upsert_import_record(
        channel_id=channel_id,
        message_id=message_id,
        media_group_id=media_group_id,
        caption=caption,
        photo_file_ids=photo_file_ids,
    )

    if media_group_id and not caption:
        leader = _find_group_leader(channel_id, media_group_id, caption)
        if leader and leader.pk != record.pk and leader.product_id:
            record.product = leader.product
            record.status = TelegramImport.STATUS_IMPORTED
            record.imported_at = leader.imported_at
            record.save(update_fields=["status", "product", "imported_at", "updated_at"])
            if leader.product_id and photo_file_ids:
                _sync_images(leader.product, record, leader.product.name)
            return record

    if not photo_file_ids and not photo_files and not caption:
        record.status = TelegramImport.STATUS_SKIPPED
        record.error = "Порожнє повідомлення"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    if photo_files:
        photo_files = rank_photo_files(photo_files)
    if not photo_files and not photo_file_ids and not caption.strip():
        record.status = TelegramImport.STATUS_SKIPPED
        record.error = "Немає придатного фото"
        record.save(update_fields=["status", "error", "updated_at"])
        return record

    default_brand = _default_brand()
    default_category = _default_category()
    if not default_brand or not default_category:
        record.status = TelegramImport.STATUS_FAILED
        record.error = "Не знайдено дефолтний бренд або категорію"
        record.save(update_fields=["status", "error", "updated_at"])
        raise ImportError(record.error)

    parsed = parse_caption(
        caption or record.raw_caption,
        default_brand=default_brand,
        default_category=default_category,
        default_gender=settings.TELEGRAM_DEFAULT_GENDER,
    )

    if not parsed.brand or not parsed.category:
        record.status = TelegramImport.STATUS_FAILED
        record.error = "Не вдалося визначити бренд або категорію"
        record.save(update_fields=["status", "error", "updated_at"])
        raise ImportError(record.error)

    default_price = Decimal(settings.TELEGRAM_DEFAULT_PRICE)
    base_price = parsed.base_price or default_price

    product = record.product
    if not product:
        product = Product.objects.create(
            brand=parsed.brand,
            category=parsed.category,
            name=parsed.name,
            description=parsed.description,
            gender=parsed.gender,
            base_price=base_price,
            is_active=settings.TELEGRAM_IMPORT_AS_ACTIVE,
        )
        record.product = product
    else:
        product.brand = parsed.brand
        product.category = parsed.category
        product.name = parsed.name
        product.description = parsed.description
        product.gender = parsed.gender
        product.base_price = base_price
        product.save()

    _sync_variants(
        product,
        channel_id=channel_id,
        message_id=message_id,
        parsed_variants=parsed.variants,
        default_price=default_price,
    )
    _sync_images(product, record, parsed.name, photo_files=photo_files)

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
    logger.info("Імпортовано товар %s з TG %s/%s", product.pk, channel_id, message_id)
    return record
