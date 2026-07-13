from django.core.management.base import BaseCommand
from django.db import transaction

from src.telegram_import.models import TelegramImport
from src.telegram_import.services.importer import _default_brand, _default_category
from src.telegram_import.services.parser import parse_caption


class Command(BaseCommand):
    help = (
        "Перепарсити name і description товарів із збереженого raw_caption. "
        "Потрібно після змін у parser.py без повторного імпорту фото."
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
        scanned = 0
        changed = 0

        for record in qs.iterator():
            scanned += 1
            product = record.product
            parsed = parse_caption(
                record.raw_caption,
                default_brand=default_brand,
                default_category=default_category,
                default_gender=product.gender or "U",
            )

            updates: dict[str, str] = {}
            if parsed.name and product.name != parsed.name:
                updates["name"] = parsed.name
            if product.description != parsed.description:
                updates["description"] = parsed.description

            if not updates:
                continue

            changed += 1
            preview = f"TG {record.message_id} · {product.pk}"
            if "name" in updates:
                preview += f"\n  name: {product.name[:72]!r}"
                preview += f"\n     → {updates['name']!r}"
            if "description" in updates:
                preview += f"\n  description: {len(product.description)} → {len(updates['description'])} chars"

            if dry_run:
                self.stdout.write(preview)
                continue

            with transaction.atomic():
                for field, value in updates.items():
                    setattr(product, field, value)
                product.save(update_fields=list(updates.keys()))

            self.stdout.write(self.style.SUCCESS(preview))

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: переглянуто {scanned}, оновлено {changed}"
            )
        )
