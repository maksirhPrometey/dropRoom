"""
Одноразове очищення вже накопичених дублікатів зображень товару.

Причина дублів: повторна ресинхронізація того самого допису (повторний
caption, повторний прихід медіа-групи) щоразу перечитувала вже збережені
фото поруч із новими без дедуплікації за вмістом — і `.all().delete()`
чистив лише записи в БД, а не самі файли на диску. Сам баг вже виправлено
в `rank_photo_files`/`_sync_images`; ця команда — лише розчищення того,
що вже накопичилось раніше.
"""

import hashlib

from django.core.management.base import BaseCommand

from src.catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Прибрати побайтово однакові дублікати ProductImage в кожному товарі."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати, що буде видалено, без змін у БД.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        products_affected = 0
        images_removed = 0

        for product in Product.objects.prefetch_related("images"):
            images = list(product.images.order_by("sort_order", "pk"))
            if len(images) < 2:
                continue

            seen: dict[str, ProductImage] = {}
            duplicates: list[ProductImage] = []
            for image in images:
                if not image.image:
                    continue
                try:
                    with image.image.open("rb") as handle:
                        digest = hashlib.md5(handle.read()).hexdigest()
                except (OSError, ValueError):
                    continue
                if digest in seen:
                    duplicates.append(image)
                else:
                    seen[digest] = image

            if not duplicates:
                continue

            products_affected += 1
            preview = (
                f"product {product.pk} {product.name[:50]!r}: "
                f"{len(images)} фото → лишиться {len(images) - len(duplicates)}, "
                f"видаляю {len(duplicates)} дублів"
            )

            if dry_run:
                self.stdout.write(preview)
                images_removed += len(duplicates)
                continue

            for image in duplicates:
                if image.image:
                    image.image.delete(save=False)
                image.delete()
            # Перенумерувати sort_order без прогалин, щоб перше фото
            # лишалось головним (is_primary), а порядок галереї не «стрибав».
            remaining = product.images.order_by("sort_order", "pk")
            for index, image in enumerate(remaining):
                update_fields = []
                if image.sort_order != index:
                    image.sort_order = index
                    update_fields.append("sort_order")
                if image.is_primary != (index == 0):
                    image.is_primary = index == 0
                    update_fields.append("is_primary")
                if update_fields:
                    image.save(update_fields=update_fields)

            images_removed += len(duplicates)
            self.stdout.write(self.style.SUCCESS(preview))

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: товарів із дублями {products_affected}, "
                f"видалено фото {images_removed}"
            )
        )
