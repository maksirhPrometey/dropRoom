from decimal import Decimal

from django.test import TestCase

from src.catalog.models import Brand, Category
from src.telegram_import.services.parser import parse_caption


CARDIGAN = """Кардиган Polo Ralph Lauren

Елегантний кардиган, який стане базою гардероба на будь-який сезон.

• XS — ОГ 80–84 см | довжина 52 см
🏷️ 3550 грн
• S — ОГ 84–88 см | довжина 53 см
🏷️ 3720 грн
• M — ОГ 88–92 см | довжина 54 см
🏷️ 3890 грн
• L — ОГ 92–96 см | довжина 55 см
🏷️ 4050 грн

на всі кольори ціна однакова"""

COACH_BAG = """Coach Straw Tote Bag ❤️🤍

Стильна літня сумка-шопер із соломʼяного плетіння.

📏 Розміри:
Ширина — 40 см
Висота — 30 см

🏷️ 6050"""

BEAR_SWEATER = """✨ Ralph Lauren Bear Sweater

Елегантний в'язаний светр Ralph Lauren із культовим ведмедиком Polo Bear.

Розміри та ціни:
XS — 5250
✅ S — 5450 грн
✅ M — 4899 грн
✅ L — 5050 грн"""

BEAR_SOLD_OUT = """✨ Ralph Lauren Bear Sweater

Елегантний в'язаний светр Ralph Lauren.

Розміри та ціни:
❌ XS — Sold Out
✅ S — 5050 грн
✅ M — 4899 грн
✅ L — 5050 грн"""

ZARA_SLIPPERS = """Шльопанці Zara

Коричневі

📏 Розмірна сітка
• 35 — 22 см — 🏷️ 1790 грн
• 38 — 23,5 см — 🏷️ 1820 грн ❌

Чорні

📏 Розмірна сітка
• 38 — 23,5 см — 🏷️ 1820 грн ( 1 пара є в наявності )

леопардові

📏 Розмірна сітка
• 42 — 25,5 см — 🏷️ 1850 грн"""

UGG_VENTURE_DAZE = """UGG Venture Daze — стильні сандалі на масивній платформі, які поєднують комфорт, легкість і сучасний дизайн. М’яка анатомічна устілка, регульована шнурівка та амортизуюча підошва забезпечують максимальну зручність протягом усього дня. Ідеальний вибір для літніх образів.

📏 Розміри та ціни:
🔹 34 (21,5 см) — 3 850 грн
🔹 35 (22 см) — 3 950 грн
🔹 36 (23 см) — 4 050 грн
🔹 37 (23,5 см) — 4 150 грн
🔹 38 (24 см) — 4 250 грн
🔹 39 (25 см) — 4 350 грн
🔹 40 (25,5 см) — 4 450 грн

всі кольори в одну ціну"""


POLO_CAP = """В наявності кепка Polo 

one size

- 50 % 

🏷️999"""


class ChannelCaptionParserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand, _ = Brand.objects.get_or_create(
            name="Polo Ralph Lauren",
            defaults={"slug": "polo-ralph-lauren"},
        )
        Brand.objects.get_or_create(name="Coach", defaults={"slug": "coach"})
        Brand.objects.get_or_create(name="Zara", defaults={"slug": "zara"})
        Brand.objects.get_or_create(name="UGG", defaults={"slug": "ugg"})
        cls.knitwear, _ = Category.objects.get_or_create(
            slug="knitwear",
            defaults={"name": "Knitwear"},
        )
        Category.objects.get_or_create(slug="bags", defaults={"name": "Bags"})
        Category.objects.get_or_create(slug="footwear", defaults={"name": "Footwear"})
        Category.objects.get_or_create(
            slug="accessories",
            defaults={"name": "Accessories"},
        )
        Brand.objects.get_or_create(name="Crocs", defaults={"slug": "crocs"})

    def _parse(self, caption: str):
        return parse_caption(
            caption,
            default_brand=self.brand,
            default_category=self.knitwear,
            default_gender="U",
        )

    def test_cardigan_title_brand_and_size_prices(self):
        parsed = self._parse(CARDIGAN)
        self.assertEqual(parsed.name, "Кардиган Polo Ralph Lauren")
        self.assertEqual(parsed.brand.name, "Polo Ralph Lauren")
        self.assertEqual(parsed.category.slug, "knitwear")
        self.assertEqual(len(parsed.variants), 4)
        self.assertEqual(parsed.variants[0].size, "XS")
        self.assertEqual(parsed.variants[0].price, Decimal("3550"))
        self.assertEqual(parsed.variants[-1].price, Decimal("4050"))
        self.assertEqual(parsed.base_price, Decimal("3550"))

    def test_coach_bag_single_price(self):
        parsed = self._parse(COACH_BAG)
        self.assertEqual(parsed.name, "Coach Straw Tote Bag")
        self.assertEqual(parsed.brand.name, "Coach")
        self.assertEqual(parsed.category.slug, "bags")
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.variants[0].size, "ONE SIZE")
        self.assertEqual(parsed.variants[0].price, Decimal("6050"))
        self.assertEqual(parsed.variants[0].stock_qty, 0)

    def test_bear_sweater_sizes_and_prices(self):
        parsed = self._parse(BEAR_SWEATER)
        self.assertEqual(parsed.name, "Ralph Lauren Bear Sweater")
        self.assertEqual(parsed.brand.name, "Polo Ralph Lauren")
        self.assertEqual(len(parsed.variants), 4)
        self.assertEqual(parsed.variants[1].size, "S")
        self.assertEqual(parsed.variants[1].price, Decimal("5450"))
        self.assertEqual(parsed.variants[2].price, Decimal("4899"))

    def test_bear_sweater_sold_out_variant(self):
        parsed = self._parse(BEAR_SOLD_OUT)
        xs = next(v for v in parsed.variants if v.size == "XS")
        self.assertFalse(xs.is_available)
        self.assertEqual(xs.stock_qty, 0)
        s = next(v for v in parsed.variants if v.size == "S")
        self.assertTrue(s.is_available)

    def test_zara_slippers_colors_stock_and_sold_out(self):
        parsed = self._parse(ZARA_SLIPPERS)
        self.assertEqual(parsed.name, "Шльопанці Zara")
        self.assertEqual(parsed.brand.name, "Zara")
        self.assertEqual(parsed.category.slug, "footwear")
        self.assertGreaterEqual(len(parsed.variants), 4)

        brown_38 = next(
            v for v in parsed.variants if v.size == "38" and v.color == "Коричневі"
        )
        self.assertFalse(brown_38.is_available)

        black_38 = next(
            v for v in parsed.variants if v.size == "38" and v.color == "Чорні"
        )
        self.assertTrue(black_38.is_available)
        self.assertEqual(black_38.stock_qty, 1)

        leopard_42 = next(
            v for v in parsed.variants if v.size == "42" and v.color == "леопардові"
        )
        self.assertEqual(leopard_42.price, Decimal("1850"))

    def test_inline_title_lead_splits_name_and_description(self):
        parsed = self._parse(UGG_VENTURE_DAZE)
        self.assertEqual(parsed.name, "UGG Venture Daze")
        self.assertIn("стильні сандалі", parsed.description)
        self.assertIn("літніх образів", parsed.description)
        self.assertNotIn("Розміри та ціни", parsed.description)
        self.assertNotIn("3 850 грн", parsed.description)

    def test_polo_cap_strips_availability_and_matches_brand(self):
        parsed = self._parse(POLO_CAP)
        self.assertEqual(parsed.name, "Кепка Polo")
        self.assertEqual(parsed.brand.name, "Polo Ralph Lauren")
        self.assertEqual(parsed.category.slug, "accessories")
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.variants[0].size, "ONE SIZE")
        self.assertEqual(parsed.variants[0].price, Decimal("999"))
        self.assertEqual(parsed.variants[0].stock_qty, 1)
