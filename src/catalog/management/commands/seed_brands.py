from django.core.management.base import BaseCommand

from src.catalog.models import Brand

BRANDS = [
    ("Crocs", "crocs", "USA"),
    ("Coach", "coach", "USA"),
    ("Karl Lagerfeld", "karl-lagerfeld", "France"),
    ("Polo Ralph Lauren", "polo-ralph-lauren", "USA"),
    ("Nike", "nike", "USA"),
    ("Adidas", "adidas", "Germany"),
    ("Zara", "zara", "Spain"),
    ("Tommy Hilfiger", "tommy-hilfiger", "USA"),
    ("Acne Studios", "acne-studios", "Sweden"),
    ("Lacoste", "lacoste", "France"),
    ("Love Moschino", "love-moschino", "Italy"),
    ("Skims", "skims", "USA"),
    ("Alo", "alo", "USA"),
    ("COS", "cos", "Sweden"),
    ("BOSS", "boss", "Germany"),
    ("Armani", "armani", "Italy"),
    ("Max Mara", "max-mara", "Italy"),
    ("Massimo Dutti", "massimo-dutti", "Spain"),
    ("Tory Burch", "tory-burch", "USA"),
    ("On Running", "on-running", "Switzerland"),
    ("Pinko", "pinko", "Italy"),
    ("Tom Ford", "tom-ford", "USA"),
    ("Michael Kors", "michael-kors", "USA"),
    ("Birkenstock", "birkenstock", "Germany"),
    ("UGG", "ugg", "USA"),
]


class Command(BaseCommand):
    help = "Seed initial brand data"

    def handle(self, *args, **options):
        created_count = 0
        for name, slug, country in BRANDS:
            _, created = Brand.objects.get_or_create(
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
