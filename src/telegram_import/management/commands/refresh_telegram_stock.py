from decimal import Decimal

from django.conf import settings
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
        "Перепарсити варіанти (ціна, stock, наявність) і base_price із raw_caption. "
        "Для кожного товару береться найповніший caption (найдовший)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати зміни без запису в БД",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Оновити навіть якщо значення виглядають такими ж",
        )
        parser.add_argument(
            "--slug",
            default="",
            help="Оновити лише товар з цим slug",
        )

    def handle(self, *args, **options):
        # Дефолти опційні: парсер бере brand/category з caption;
        # якщо немає — лишаємо поточні значення товару.
        default_brand = _default_brand()
        default_category = _default_category()

        dry_run = options["dry_run"]
        force = options["force"]
        slug = (options["slug"] or "").strip()
        scanned = 0
        changed = 0

        qs = (
            TelegramImport.objects.filter(
                product_id__isnull=False,
                status=TelegramImport.STATUS_IMPORTED,
            )
            .exclude(raw_caption="")
            .select_related("product")
            .order_by("message_id")
        )
        if slug:
            qs = qs.filter(product__slug=slug)

        # Один товар може мати кілька TG-записів (альбом) — беремо найдовший caption.
        best_by_product: dict[int, TelegramImport] = {}
        for record in qs.iterator():
            current = best_by_product.get(record.product_id)
            if current is None or len(record.raw_caption) > len(current.raw_caption):
                best_by_product[record.product_id] = record

        for record in best_by_product.values():
            scanned += 1
            product = record.product
            parsed = parse_caption(
                record.raw_caption,
                default_brand=default_brand or product.brand,
                default_category=default_category or product.category,
                default_gender=product.gender or "U",
            )
            if not parsed.variants:
                self.stdout.write(
                    self.style.WARNING(
                        f"TG {record.message_id} · {product.pk} {product.slug}: "
                        f"варіанти не розпарсилися"
                    )
                )
                continue

            db_variants = list(
                product.variants.order_by("size", "color__name").values_list(
                    "size", "stock_qty", "price", "is_available"
                )
            )
            parsed_variants = sorted(
                (
                    v.size,
                    v.stock_qty,
                    v.price,
                    v.is_available,
                )
                for v in parsed.variants
            )
            base_price = parsed.base_price
            base_price_changed = (
                base_price is not None and product.base_price != base_price
            )
            if (
                not force
                and db_variants == parsed_variants
                and not base_price_changed
            ):
                continue

            changed += 1
            preview = (
                f"TG {record.message_id} · {product.pk} {product.slug}\n"
                f"  name: {product.name[:60]!r}\n"
                f"  variants: {db_variants} → {parsed_variants}\n"
                f"  base_price: {product.base_price} → {base_price}"
            )
            if dry_run:
                self.stdout.write(preview)
                continue

            with transaction.atomic():
                _sync_variants(
                    product,
                    channel_id=record.channel_id,
                    message_id=record.message_id,
                    parsed_variants=parsed.variants,
                    default_price=Decimal(settings.TELEGRAM_DEFAULT_PRICE),
                )
            self.stdout.write(self.style.SUCCESS(preview))

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: переглянуто {scanned}, оновлено {changed}"
            )
        )
