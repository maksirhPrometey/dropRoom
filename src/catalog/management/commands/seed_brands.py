from django.core.management.base import BaseCommand

from src.catalog.models import Brand
from src.catalog.seed_data import BRANDS


class Command(BaseCommand):
    help = "Seed initial brand data (legacy alias for seed_catalog --brands-only)"

    def handle(self, *args, **options):
        created_count = 0
        for name, slug, country in BRANDS:
            _, created = Brand.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "country": country, "is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} brands created, {len(BRANDS) - created_count} already existed."
            )
        )
