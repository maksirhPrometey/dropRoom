from django.core.management.base import BaseCommand

from src.catalog.models import Brand, Category
from src.catalog.seed_data import BRANDS, CATEGORIES


class Command(BaseCommand):
    help = "Заповнити початкові бренди та категорії каталогу"

    def add_arguments(self, parser):
        parser.add_argument(
            "--brands-only",
            action="store_true",
            help="Лише бренди",
        )
        parser.add_argument(
            "--categories-only",
            action="store_true",
            help="Лише категорії",
        )

    def handle(self, *args, **options):
        brands_only = options["brands_only"]
        categories_only = options["categories_only"]

        if brands_only and categories_only:
            self.stderr.write(
                self.style.ERROR("Оберіть лише один з прапорців: --brands-only або --categories-only.")
            )
            return

        if not categories_only:
            self._seed_brands()
        if not brands_only:
            self._seed_categories()

    def _seed_brands(self):
        created = 0
        updated = 0

        for name, slug, country in BRANDS:
            brand, was_created = Brand.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "country": country,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  + бренд: {brand.name}")
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Бренди: створено {created}, оновлено {updated}, всього {len(BRANDS)}."
            )
        )

    def _seed_categories(self):
        created = 0
        updated = 0

        for data in CATEGORIES:
            slug = data["slug"]
            category, was_created = Category.objects.update_or_create(
                slug=slug,
                defaults=data,
            )
            if was_created:
                created += 1
                self.stdout.write(f"  + категорія: {category.name}")
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Категорії: створено {created}, оновлено {updated}, всього {len(CATEGORIES)}."
            )
        )
