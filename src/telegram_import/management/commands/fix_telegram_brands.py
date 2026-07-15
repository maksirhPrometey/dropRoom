from django.core.management.base import BaseCommand
from django.db import transaction

from src.catalog.models import Brand
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.importer import _default_brand, _default_category
from src.telegram_import.services.parser import _match_category, resolve_brand


class Command(BaseCommand):
    help = (
        "Виправити brand (і опційно category) товарів з Telegram за raw_caption. "
        "Корисно після додавання брендів у seed / коли звалився fallback на Crocs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати зміни без запису в БД",
        )
        parser.add_argument(
            "--only-default",
            action="store_true",
            help="Оновлювати лише товари з дефолтним брендом (зазвичай Crocs)",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Створювати бренд з рядка «Бренд: …», якщо його ще немає",
        )
        parser.add_argument(
            "--with-category",
            action="store_true",
            help="Також оновити категорію з caption",
        )
        parser.add_argument(
            "--slug",
            default="",
            help="Лише товар з цим slug",
        )

    def handle(self, *args, **options):
        # --only-default: явний ID з .env або історичний fallback Crocs
        default_brand = _default_brand()
        if options["only_default"] and not default_brand:
            default_brand = Brand.objects.filter(slug="crocs", is_active=True).first()
            if not default_brand:
                self.stderr.write(
                    self.style.ERROR(
                        "Для --only-default задай TELEGRAM_DEFAULT_BRAND_ID "
                        "або май бренд зі slug=crocs"
                    )
                )
                return

        default_category = _default_category()

        dry_run = options["dry_run"]
        only_default = options["only_default"]
        create_missing = options["create_missing"]
        with_category = options["with_category"]
        slug = (options["slug"] or "").strip()

        qs = (
            TelegramImport.objects.filter(
                product_id__isnull=False,
                status=TelegramImport.STATUS_IMPORTED,
            )
            .exclude(raw_caption="")
            .select_related("product", "product__brand", "product__category")
            .order_by("message_id")
        )
        if slug:
            qs = qs.filter(product__slug=slug)

        best_by_product: dict[int, TelegramImport] = {}
        for record in qs.iterator():
            current = best_by_product.get(record.product_id)
            if current is None or len(record.raw_caption) > len(current.raw_caption):
                best_by_product[record.product_id] = record

        scanned = 0
        changed = 0
        skipped_no_brand = 0

        for record in best_by_product.values():
            scanned += 1
            product = record.product

            if only_default and (
                not default_brand or product.brand_id != default_brand.pk
            ):
                continue

            brand = resolve_brand(
                record.raw_caption,
                create_missing=create_missing and not dry_run,
            )
            # dry-run: показати потенційне створення без запису
            if brand is None and create_missing and dry_run:
                from src.telegram_import.services.parser import _extract_brand_label

                label = _extract_brand_label(record.raw_caption)
                if label:
                    self.stdout.write(
                        f"TG {record.message_id} · {product.slug}: "
                        f"створив би бренд {label!r}"
                    )

            if brand is None:
                skipped_no_brand += 1
                continue

            updates: dict[str, object] = {}
            if product.brand_id != brand.pk:
                updates["brand"] = brand

            if with_category and default_category:
                category = _match_category(record.raw_caption)
                if category and product.category_id != category.pk:
                    updates["category"] = category

            if not updates:
                continue

            changed += 1
            preview = f"TG {record.message_id} · {product.pk} {product.slug}"
            preview += f"\n  name: {product.name[:72]!r}"
            if "brand" in updates:
                preview += f"\n  brand: {product.brand.name} → {updates['brand'].name}"
            if "category" in updates:
                preview += (
                    f"\n  category: {product.category.slug} → {updates['category'].slug}"
                )

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
                f"Готово{suffix}: переглянуто {scanned}, оновлено {changed}, "
                f"без бренду в тексті {skipped_no_brand}"
            )
        )
