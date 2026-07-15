from decimal import Decimal

from django.test import TestCase

from src.catalog.models import Brand, Category
from src.telegram_import.services.parser import parse_caption


class BotGroupFormatTests(TestCase):
    def setUp(self):
        defaults = {"is_active": True}
        for name, slug in (
            ("Lacoste", "lacoste"),
            ("Karl Lagerfeld", "karl-lagerfeld"),
            ("Massimo Dutti", "massimo-dutti"),
            ("Tory Burch", "tory-burch"),
            ("Levi's", "levis"),
            ("Maison Margiela", "maison-margiela"),
            ("Tom Ford", "tom-ford"),
        ):
            Brand.objects.get_or_create(slug=slug, defaults={"name": name, **defaults})
        for name, slug in (
            ("Dresses", "dresses"),
            ("Outerwear", "outerwear"),
            ("Sneakers", "sneakers"),
            ("Tops", "tops"),
            ("Accessories", "accessories"),
            ("Loungewear", "loungewear"),
        ):
            Category.objects.get_or_create(slug=slug, defaults={"name": name})

    def _parse(self, caption: str):
        return parse_caption(
            caption,
            default_brand=None,
            default_category=None,
            default_gender="U",
        )

    def test_lacoste_comma_sizes(self):
        parsed = self._parse(
            "Сукня Lacoste Polo\n"
            "Бренд: Lacoste\n\n"
            "Розмір:\n"
            "S - 🏷️ 4499 грн ( в наявності )\n"
            "M, L, XL - 🏷️ 4350 грн ( під замовлення)\n"
        )
        self.assertEqual(parsed.category.slug, "dresses")
        by_size = {v.size: v for v in parsed.variants}
        self.assertEqual(set(by_size), {"S", "M", "L", "XL"})
        self.assertEqual(by_size["S"].price, Decimal("4499"))
        self.assertEqual(by_size["S"].stock_qty, 1)
        self.assertEqual(by_size["M"].price, Decimal("4350"))
        self.assertEqual(by_size["M"].stock_qty, 0)
        self.assertIsNone(by_size["M"].color)

    def test_massimo_cyrillic_sizes_block(self):
        parsed = self._parse(
            "Massimo Dutti пуховик\n"
            "Бренд: Massimo Dutti\n\n"
            "с , м та л  під замовлення\n"
            "🏷️8950\n"
        )
        self.assertEqual(parsed.category.slug, "outerwear")
        sizes = {v.size for v in parsed.variants}
        self.assertEqual(sizes, {"S", "M", "L"})
        self.assertTrue(all(v.price == Decimal("8950") for v in parsed.variants))

    def test_karl_vest_cyrillic_color_prices(self):
        parsed = self._parse(
            "Karl Lagerfeld жилетка\n"
            "Бренд: Karl Lagerfeld\n\n"
            "Чорний\n"
            "с під замовлення  4050\n"
            "м під замовлення  3950\n"
            "л під замовлення  3790\n"
            "хл під замовлення  4250\n\n"
            "Біла\n"
            "с під замовлення 3999\n"
            "м під замовлення  4230\n"
        )
        self.assertEqual(parsed.category.slug, "outerwear")
        black_s = next(
            v for v in parsed.variants if v.size == "S" and v.color == "Чорний"
        )
        self.assertEqual(black_s.price, Decimal("4050"))
        white_m = next(
            v for v in parsed.variants if v.size == "M" and v.color == "Біла"
        )
        self.assertEqual(white_m.price, Decimal("4230"))

    def test_tory_ruler_size(self):
        parsed = self._parse(
            "Tory Burch кеди\n"
            "Бренд: Tory Burch\n\n"
            "📏38 - в наявності 1 пара\n"
        )
        self.assertEqual(parsed.category.slug, "sneakers")
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.variants[0].size, "38")
        self.assertEqual(parsed.variants[0].stock_qty, 1)

    def test_levis_brand_and_sizes(self):
        parsed = self._parse(
            "Футболка Levi’s Batwing Logo\n"
            "Бренд: Levis\n\n"
            "Біла Л - 🏷️ 1150грн ( в наявності 1 штука )\n"
            "Біла S, M, XL, 2XL -🏷️ 1399 грн( під замовлення )\n"
            "Чорна S, M, L -🏷️ 1399 грн ( під замовлення)\n"
        )
        self.assertEqual(parsed.brand.name, "Levi's")
        self.assertEqual(parsed.category.slug, "tops")
        white_l = next(
            v for v in parsed.variants if v.size == "L" and v.color == "Біла"
        )
        self.assertEqual(white_l.price, Decimal("1150"))
        self.assertEqual(white_l.stock_qty, 1)

    def test_tom_ford_sunglasses_category(self):
        parsed = self._parse(
            "TOM FORD - Turner Square-Frame Acetate Sunglasses - 50 %\n\n"
            "🏷️7250 - під замовлення\n"
        )
        self.assertEqual(parsed.brand.name, "Tom Ford")
        self.assertEqual(parsed.category.slug, "accessories")

    def test_karl_suit_loungewear(self):
        parsed = self._parse(
            "Karl Lagerfeld\n"
            "Бренд: Karl Lagerfeld\n\n"
            "Стильний трикотажний костюм у спортивному стилі.\n\n"
            "XS — 🏷️ 3950 грн під замовлення\n"
            "S — 🏷️ 4050 грн під замовлення\n"
        )
        self.assertEqual(parsed.category.slug, "loungewear")

    def test_square_bullet_size_lines_not_treated_as_colors(self):
        parsed = self._parse(
            "Бомбер Massimo Dutti 🤍\n"
            "Бренд: Massimo Dutti\n\n"
            "▫️XS — 🏷️ 2450 грн\n"
            "▫️S — 🏷️ 2590 грн\n"
            "▫️M — 🏷️ 2790 грн\n"
            "▫️L — 🏷️ 2950 грн\n"
        )
        sizes = [v.size for v in parsed.variants]
        self.assertEqual(sorted(sizes), ["L", "M", "S", "XS"])
        self.assertEqual(len(sizes), len(set(sizes)))
        self.assertTrue(all(v.color is None for v in parsed.variants))

    def test_size_with_foot_length_note_and_color_sections(self):
        parsed = self._parse(
            "Сапоги Massimo Dutti\n"
            "Бренд: Massimo Dutti\n\n"
            "Шоколадні \n\n"
            "Ціна:\n\n"
            "35 (22,5 см) — 7250 грн\n"
            "36 (23,0 см) — 7290 грн\n\n"
            "чорні \n\n"
            "Ціна:\n\n"
            "35 (22,5 см) — 7250 грн\n"
            "36 (23,0 см) — 7290 грн\n"
        )
        pairs = {(v.size, v.color) for v in parsed.variants}
        self.assertEqual(
            pairs,
            {
                ("35", "Шоколадні"),
                ("36", "Шоколадні"),
                ("35", "чорні"),
                ("36", "чорні"),
            },
        )
        self.assertEqual(len(parsed.variants), 4)

    def test_color_strips_preorder_word(self):
        parsed = self._parse(
            "Пуховик Karl Lagerfeld\n"
            "Бренд: Karl Lagerfeld\n\n"
            "Чорний  під замовлення\n"
            "XS — 🏷️ 5650 грн\n"
            "S — 🏷️ 5950 грн\n"
        )
        self.assertTrue(all(v.color == "Чорний" for v in parsed.variants))
        self.assertFalse(
            any(v.color and "під замовлення" in v.color for v in parsed.variants)
        )
