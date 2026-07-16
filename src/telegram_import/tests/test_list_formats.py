from decimal import Decimal

from django.test import TestCase

from src.catalog.models import Brand, Category
from src.telegram_import.services.parser import parse_caption
from src.telegram_import.services.parser_list_formats import (
    extract_kids_age_variants,
    extract_semicolon_tier_variants,
    extract_stock_csv_variants,
)


ADIDAS_STOCK_CSV = """Кросівки унісекс Adidas Xlg Runner Deluxe White JR0577

У наявності: 37, 39
Під замовлення: 36, 36.5, 37, 38, 38.5, 39, 40, 40.5, 41, 42, 42.5, 43, 44, 45

🏷️8200"""

TIER_SEMICOLON = """в наявності 📏40 🏷️5050

36 ; 36 ,5 ; 38 🏷️5150

37 ; 37,5 ; 38,5 🏷️5450

44,5 ; 45 Sold out❌"""

KIDS_POLO = """Дитяча футболка Polo Ralph Lauren

2 роки - 1050
5 років - 1190
6 роки - 1190
8-10 роки - 1230"""

NIKE_SIZE_DASH = """Nike Mind 001 Slide Black Chrome

39 — 5490 грн
40 — 5690 грн
41 — 5890 грн
44 — 6890 грн в наявності"""


class ListFormatVariantsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand, _ = Brand.objects.get_or_create(
            name="Adidas",
            defaults={"slug": "adidas"},
        )
        Brand.objects.get_or_create(
            name="Polo Ralph Lauren",
            defaults={"slug": "polo-ralph-lauren"},
        )
        Brand.objects.get_or_create(name="Nike", defaults={"slug": "nike"})
        cls.sneakers, _ = Category.objects.get_or_create(
            slug="sneakers",
            defaults={"name": "Sneakers"},
        )
        Category.objects.get_or_create(slug="knitwear", defaults={"name": "Knitwear"})

    def _parse(self, caption: str):
        return parse_caption(
            caption,
            default_brand=self.brand,
            default_category=self.sneakers,
            default_gender="U",
        )

    def test_stock_csv_avail_and_preorder(self):
        variants = extract_stock_csv_variants(ADIDAS_STOCK_CSV)
        self.assertIsNotNone(variants)
        by_size = {item.size: item for item in variants}
        self.assertEqual(by_size["37"].stock_qty, 1)
        self.assertEqual(by_size["37"].price, Decimal("8200"))
        self.assertEqual(by_size["36.5"].stock_qty, 0)
        self.assertEqual(by_size["45"].price, Decimal("8200"))
        self.assertGreaterEqual(len(variants), 14)

        parsed = self._parse(ADIDAS_STOCK_CSV)
        self.assertEqual(parsed.name, "Кросівки унісекс Adidas Xlg Runner Deluxe White JR0577")
        self.assertEqual(parsed.brand.name, "Adidas")
        self.assertEqual(len(parsed.variants), len(variants))

    def test_semicolon_tier_prices(self):
        variants = extract_semicolon_tier_variants(TIER_SEMICOLON)
        self.assertIsNotNone(variants)
        by_size = {item.size: item for item in variants}
        self.assertEqual(by_size["36"].price, Decimal("5150"))
        self.assertEqual(by_size["36.5"].price, Decimal("5150"))
        self.assertEqual(by_size["37.5"].price, Decimal("5450"))
        self.assertFalse(by_size["45"].is_available)

    def test_kids_age_prices(self):
        variants = extract_kids_age_variants(KIDS_POLO)
        self.assertIsNotNone(variants)
        self.assertGreaterEqual(len(variants), 3)
        parsed = self._parse(KIDS_POLO)
        self.assertTrue(parsed.name.startswith("Дитяча футболка"))
        sizes = {item.size for item in parsed.variants}
        self.assertIn("2 роки", sizes)
        self.assertIn("8-10 роки", sizes)

    def test_size_dash_still_works(self):
        parsed = self._parse(NIKE_SIZE_DASH)
        self.assertEqual(parsed.name, "Nike Mind 001 Slide Black Chrome")
        by_size = {item.size: item for item in parsed.variants}
        self.assertEqual(by_size["39"].price, Decimal("5490"))
        self.assertEqual(by_size["44"].stock_qty, 1)

    def test_availability_prefix_with_emoji(self):
        parsed = self._parse(
            "В наявності 🤍 Pinko Beige Sneakers\n\n"
            "🔹 38 — 5650 грн\n"
            "🔹 40 — 5650 грн"
        )
        self.assertEqual(parsed.name, "Pinko Beige Sneakers")
        self.assertEqual(len(parsed.variants), 2)
