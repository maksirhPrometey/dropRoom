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
        "Перерахувати stock_qty варіантів із raw_caption. "
        "За замовчуванням — під замовлення (0), наявність лише за явним сигналом у тексті."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати зміни без запису в БД",
        )

    def handle(self, *args, **options):
        default_brand = _default_brand()
        default_category = _default_category()
        if not default_brand or not default_category:
            self.stderr.write(self.style.ERROR("Не знайдено дефолтний бренд або категорію"))
            return

        dry_run = options["dry_run"]
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

        for record in qs.iterator():
            scanned += 1
            product = record.product
            parsed = parse_caption(
                record.raw_caption,
                default_brand=default_brand,
                default_category=default_category,
                default_gender=product.gender or "U",
            )
            if not parsed.variants:
                continue

            db_stocks = list(
                product.variants.order_by("size").values_list("size", "stock_qty")
            )
            parsed_stocks = sorted((v.size, v.stock_qty) for v in parsed.variants)
            if db_stocks == parsed_stocks:
                continue

            changed += 1
            preview = (
                f"TG {record.message_id} · {product.pk} {product.name[:48]!r}\n"
                f"  {db_stocks} → {parsed_stocks}"
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
