import io
from collections import defaultdict

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from src.telegram_import.models import TelegramImport
from src.telegram_import.services.importer import _default_brand, _default_category
from src.telegram_import.services.parser import parse_caption
from src.telegram_import.services.photo_utils import normalize_product_image, photo_score


def _image_metrics(product) -> tuple[int, int]:
    primary = product.images.filter(is_primary=True).first() or product.images.first()
    if not primary or not primary.image:
        return 0, 0
    try:
        with primary.image.open("rb") as handle:
            content = handle.read()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
        return width * height, photo_score(width, height)
    except OSError:
        return 0, 0


class Command(BaseCommand):
    help = (
        "Обʼєднати дублікати Telegram-товарів з однаковим raw_caption. "
        "Лишає товар із найкращим фото, оновлює name/brand/description."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати план без змін у БД",
        )

    def handle(self, *args, **options):
        default_brand = _default_brand()
        default_category = _default_category()

        dry_run = options["dry_run"]
        groups: dict[str, list[TelegramImport]] = defaultdict(list)

        qs = (
            TelegramImport.objects.filter(
                product_id__isnull=False,
                status=TelegramImport.STATUS_IMPORTED,
            )
            .exclude(raw_caption="")
            .select_related("product", "product__brand", "product__category")
            .order_by("message_id")
        )
        for record in qs:
            groups[record.raw_caption.strip()].append(record)

        merged = 0
        removed = 0

        for caption, records in groups.items():
            if len(records) < 2:
                continue

            ranked = sorted(
                records,
                key=lambda item: (
                    _image_metrics(item.product)[0],
                    _image_metrics(item.product)[1],
                    -item.message_id,
                ),
                reverse=True,
            )
            survivor = ranked[0]
            duplicates = ranked[1:]

            parsed = parse_caption(
                caption,
                default_brand=default_brand or survivor.product.brand,
                default_category=default_category or survivor.product.category,
                default_gender=survivor.product.gender or "U",
            )

            new_brand = parsed.brand or survivor.product.brand
            new_category = parsed.category or survivor.product.category

            preview = (
                f"caption: {caption[:60]!r}…\n"
                f"  keep product {survivor.product_id} (TG {survivor.message_id})\n"
                f"  remove: {[r.product_id for r in duplicates]}"
            )
            if parsed.name != survivor.product.name or new_brand != survivor.product.brand:
                preview += (
                    f"\n  rename: {survivor.product.name!r} → {parsed.name!r}\n"
                    f"  brand: {survivor.product.brand.name} → {new_brand.name}"
                )

            if dry_run:
                self.stdout.write(preview)
                merged += 1
                removed += len(duplicates)
                continue

            with transaction.atomic():
                product = survivor.product
                product.brand = new_brand
                product.category = new_category
                product.name = parsed.name
                product.description = parsed.description
                product.save()

                primary = product.images.filter(is_primary=True).first() or product.images.first()
                if primary and primary.image:
                    with primary.image.open("rb") as handle:
                        normalized = normalize_product_image(handle.read())
                    primary.image.save(
                        primary.image.name.rsplit("/", 1)[-1],
                        ContentFile(normalized),
                        save=True,
                    )

                for record in duplicates:
                    dup_product = record.product
                    record.product = product
                    record.save(update_fields=["product", "updated_at"])
                    if dup_product.pk != product.pk:
                        dup_product.delete()
                        removed += 1

            merged += 1
            self.stdout.write(self.style.SUCCESS(preview))

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: груп {merged}, видалено дублікатів {removed}"
            )
        )
