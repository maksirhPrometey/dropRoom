from django.core.management.base import BaseCommand
from django.db import transaction

from src.telegram_import.models import TelegramImport
from src.telegram_import.services.importer import (
    _default_brand,
    _default_category,
    _sync_variants,
)
from src.telegram_import.services.parser import parse_caption


class Command(BaseCommand):
    help = (
        "Перепарсити name, description, brand, category, base_price і variants "
        "із збереженого raw_caption. Після змін у parser — без повторного імпорту фото."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--message-id",
            type=int,
            default=0,
            help="Оновити лише один Telegram message_id (0 = усі)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати зміни без запису в БД",
        )
        parser.add_argument(
            "--skip-variants",
            action="store_true",
            help="Не пересинхронізовувати ProductVariant",
        )

    def handle(self, *args, **options):
        default_brand = _default_brand()
        default_category = _default_category()
        if not default_brand or not default_category:
            self.stderr.write(
                self.style.ERROR("Не знайдено дефолтний бренд або категорію")
            )
            return

        qs = (
            TelegramImport.objects.filter(
                product_id__isnull=False,
                status=TelegramImport.STATUS_IMPORTED,
            )
            .exclude(raw_caption="")
            .select_related("product")
            .order_by("message_id")
        )
        message_id = options["message_id"]
        if message_id:
            qs = qs.filter(message_id=message_id)

        dry_run = options["dry_run"]
        skip_variants = options["skip_variants"]
        scanned = 0
        changed = 0

        best_by_product: dict[int, object] = {}
        for record in qs.iterator():
            current = best_by_product.get(record.product_id)
            if current is None or len(record.raw_caption) > len(current.raw_caption):
                best_by_product[record.product_id] = record

        for record in best_by_product.values():
            scanned += 1
            product = record.product
            parsed = parse_caption(
                record.raw_caption,
                default_brand=default_brand,
                default_category=default_category,
                default_gender=product.gender or "U",
            )

            updates: dict[str, object] = {}
            if parsed.name and product.name != parsed.name:
                updates["name"] = parsed.name
            if product.description != parsed.description:
                updates["description"] = parsed.description
            if parsed.brand and product.brand_id != parsed.brand.pk:
                updates["brand"] = parsed.brand
            if parsed.category and product.category_id != parsed.category.pk:
                updates["category"] = parsed.category
            if (
                parsed.base_price is not None
                and product.base_price != parsed.base_price
            ):
                updates["base_price"] = parsed.base_price

            will_sync_variants = False
            if not skip_variants and parsed.variants:
                parsed_key = sorted(
                    (
                        variant.size,
                        (variant.color or "").casefold(),
                        str(variant.price),
                        variant.stock_qty,
                        variant.is_available,
                    )
                    for variant in parsed.variants
                )
                existing_key = sorted(
                    (
                        variant.size,
                        (variant.color.name if variant.color_id else "").casefold(),
                        str(variant.price),
                        variant.stock_qty,
                        variant.is_available,
                    )
                    for variant in product.variants.select_related("color")
                )
                will_sync_variants = parsed_key != existing_key

            if not updates and not will_sync_variants:
                continue

            changed += 1
            preview = f"TG {record.message_id} · {product.pk}"
            if "name" in updates:
                preview += f"\n  name: {product.name[:72]!r}"
                preview += f"\n     → {updates['name']!r}"
            if "description" in updates:
                preview += (
                    f"\n  description: {len(product.description)} → "
                    f"{len(updates['description'])} chars"
                )
            if "brand" in updates:
                preview += f"\n  brand: {product.brand.name} → {updates['brand'].name}"
            if "category" in updates:
                preview += (
                    f"\n  category: {product.category.slug} → "
                    f"{updates['category'].slug}"
                )
            if "base_price" in updates:
                preview += (
                    f"\n  base_price: {product.base_price} → {updates['base_price']}"
                )
            if will_sync_variants:
                preview += (
                    f"\n  variants: sync {len(parsed.variants)} "
                    f"(було {product.variants.count()})"
                )

            if dry_run:
                self.stdout.write(preview)
                continue

            with transaction.atomic():
                for field, value in updates.items():
                    setattr(product, field, value)
                if updates:
                    product.save(update_fields=list(updates.keys()))
                if will_sync_variants:
                    _sync_variants(
                        product,
                        channel_id=record.channel_id,
                        message_id=record.message_id,
                        parsed_variants=parsed.variants,
                        default_price=parsed.base_price or product.base_price,
                    )

            self.stdout.write(self.style.SUCCESS(preview))

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: переглянуто {scanned}, оновлено {changed}"
            )
        )
