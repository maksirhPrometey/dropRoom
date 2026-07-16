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


TOMMY_JEANS_CARDIGAN = """Tommy Jeans Cardigan

Елегантний кардиган Tommy Jeans — універсальна модель для повсякденного гардероба.

S — груди 88-92 см
M — груди 92-96 см
L — груди 96-100 см

під замовлення 🏷️2999"""


MOON_BOOT = """Moon Boot
Оригінальні Moon Boot із натуральної замші — культова модель, що поєднує стиль, тепло та комфорт. Ідеальний вибір для зимових образів.

Розмірна сітка:
• S — 35–38
🏷️ 6050 грн

• M — 39 - 41
🏷️ 6290 грн

• L — 42 - 44 ❌
🏷️ 6550 гр

Важливо вказати - 50 % та закинути там де знижки"""


ZARA_JACKET = """Чоловіча куртка Zara (під замовлення)

Стильна утеплена куртка від Zara у трендовому коричневому відтінку.

Розміри: S, M, L, XL

Розмірна сітка:
S — 46–48 (обхват грудей 92–96 см) — 3150 UAH
M — 48–50 (обхват грудей 96–100 см) — 3250 UAH
L — 50–52 (обхват грудей 100–104 см) — 3350 UAH
XL — 52–54 (обхват грудей 104–108 см) — 3450 UAH"""


ZARA_SKI_PUFFER = """Пуховик ZARA Ski Collection

Бренд : Zara

Стильний пуховик із зимової колекції ZARA Ski.

Розміри та ціни:
• XS — ОГ 82–86 см — 🏷️ 2950 грн
• S — ОГ 86–90 см — 🏷️ 3090 грн
• M — ОГ 90–94 см — 🏷️ 3220 грн
• L — ОГ 94–98 см — 🏷️ 3350 грн"""


ACNE_LONGSLEEVE = """Лонгслів Acne Studios

S (ПОГ 56см, довжина 69см, рукав 67см)  🏷️5250
М (ПОГ 58см, довжина 70см, рукав 68см) 🏷️5350
L ❌Sold out"""


EMPORIO_ARMANI_BAG = """Сумка Emporio Armani - 50 %

Бренд : Emporio Armani

Стильна сумка Emporio Armani — ідеальне поєднання елегантності, практичності та сучасного дизайну.

📏 Розмір:

Ширина: 33 см

🏷️4510 ( замість 8200 )"""


COACH_GRACE_BAG = """Coach Grace Top Handle Bag

Елегантна сумка Coach із гладкої натуральної шкіри — втілення класики та витонченого стилю.

📏 Розмір:

Довжина — 25 см

під замовлення 🏷️6550"""


RAY_BAN_TWO_COLORS = """Ray-Ban Octagonal Flat Lenses RB 3556N (001)
Культова модель сонцезахисних окулярів Ray-Ban.


в наявності зелена лінза 4 штуки
коричнева 2 штуки

під замовлення і в наявності на два кольори одна ціна 🏷️4550

‼️‼️‼️важливо вказати  - 50"""


COACH_SLIPPERS_NAMED_COLORS = """Coach шльопанці

М'які шкіряні шльопанці з об'ємною стібкою та фірмовим логотипом Coach.

Розмірна сітка:
35 — 22,5 см
36 — 23 см

Ціни:
35 — 🏷️4050 UAH
36 — 🏷️4080 UAH



чорні , рожеві та білі в одну ціну


чорні 37 та 39 є в наявності

решта під замовлення"""


TORY_BURCH_SLIPPERS = """Tory Burch шльопанці

Лаконічні шльопанці з гладкої натуральної шкіри та фірмовим металевим логотипом Tory Burch.


1 в наявності 38 розмір ( 24 см )

5499

під замовлення не доступні"""


NEW_BALANCE_UNDERWEAR = """Чоловіча білизна New Balance

Комфорт, який відчувається з першої хвилини.

В наявності

📏M
📏L
📏ХЛ
всі по одній

🏷️1599  UAH


під замовлення

с м л хл
🏷️1599"""


MIU_MIU_GLASSES = """Окуляри MiU Miu


Сонцезахисні окуляри

Стильна овальна модель у тонкій металевій оправі.

▫️Тонка металева оправа золотистого кольору

🩵 Колір лінз: блакитний градієнт
✨ Колір оправи: золотистий



🏷️8050  ( 2 в наявності, решта під замовлення)"""


PRL_SOCKS_ONE_SIZE = """Набір шкарпеток Polo Ralph Lauren one size : 36 - 41

Бренд: Polo Ralph Lauren

Стильний набір високих шкарпеток із фірмовим ведмедиком Polo Bear.

One Size — 1290 грн"""


PINKO_BAG_BARE_DIMENSIONS = """Сумка Pinko

Бренд : pinko

Розмір:
Не вміщує B5
Розміри:
22 x 16 *7
Можливість регулювання довжини ременя:
Так
Максимальна довжина ременя:
114 cm
Кількість кишень на блискавці:
1


В наявності на магазині 1 🏷️6450"""


MICHAEL_KORS_BAG = """Бренд: Michael Kors

Елегантна шкіряна сумка Michael Kors Pratt Medium Satchel — стильна модель на кожен день. Виконана із зернистої натуральної шкіри, має два короткі ручки та знімний регульований плечовий ремінь. Просторе основне відділення дозволяє зручно розмістити всі необхідні речі, а мінімалістичний дизайн легко поєднується з будь-яким образом.

Розмір : 29 * 22 * 13 см

Кольори та ціни:
🖤 Чорна — 🏷️ 5050 грн
💚 М’ятна — 🏷️ 4950 грн
🤎 Коричнева — 🏷️ 4890 грн"""


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
        Brand.objects.get_or_create(name="Moon Boot", defaults={"slug": "moon-boot"})
        Brand.objects.get_or_create(
            name="Massimo Dutti", defaults={"slug": "massimo-dutti"}
        )
        Brand.objects.get_or_create(
            name="Michael Kors",
            defaults={"slug": "michael-kors"},
        )
        cls.knitwear, _ = Category.objects.get_or_create(
            slug="knitwear",
            defaults={"name": "Knitwear"},
        )
        Category.objects.get_or_create(slug="bags", defaults={"name": "Bags"})
        Category.objects.get_or_create(slug="footwear", defaults={"name": "Footwear"})
        Category.objects.get_or_create(slug="sneakers", defaults={"name": "Sneakers"})
        Category.objects.get_or_create(
            slug="accessories",
            defaults={"name": "Accessories"},
        )
        Brand.objects.get_or_create(name="Crocs", defaults={"slug": "crocs"})
        Brand.objects.get_or_create(
            name="Tommy Hilfiger",
            defaults={"slug": "tommy-hilfiger"},
        )
        Brand.objects.get_or_create(name="Acne Studios", defaults={"slug": "acne-studios"})
        Brand.objects.get_or_create(
            name="Emporio Armani", defaults={"slug": "emporio-armani"}
        )
        Brand.objects.get_or_create(name="Ray-Ban", defaults={"slug": "ray-ban"})
        Brand.objects.get_or_create(name="Tory Burch", defaults={"slug": "tory-burch"})
        Brand.objects.get_or_create(name="New Balance", defaults={"slug": "new-balance"})
        Brand.objects.get_or_create(name="Miu Miu", defaults={"slug": "miu-miu"})
        Brand.objects.get_or_create(name="Pinko", defaults={"slug": "pinko"})
        Category.objects.get_or_create(slug="loungewear", defaults={"name": "Loungewear"})
        Category.objects.get_or_create(slug="tops", defaults={"name": "Tops"})
        Category.objects.get_or_create(slug="outerwear", defaults={"name": "Outerwear"})

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
        # Sold Out з price=0 не повинен обнуляти вітрину
        self.assertEqual(parsed.base_price, Decimal("4899"))

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

    def test_tommy_jeans_cardigan_sizes_and_price(self):
        parsed = self._parse(TOMMY_JEANS_CARDIGAN)
        self.assertEqual(parsed.name, "Tommy Jeans Cardigan")
        self.assertEqual(parsed.brand.name, "Tommy Hilfiger")
        self.assertEqual(parsed.category.slug, "knitwear")
        self.assertEqual(parsed.base_price, Decimal("2999"))
        sizes = {variant.size for variant in parsed.variants}
        self.assertEqual(sizes, {"S", "M", "L"})
        for variant in parsed.variants:
            self.assertEqual(variant.price, Decimal("2999"))
            self.assertEqual(variant.stock_qty, 0)

    def test_moon_boot_size_range_uses_tag_price_not_eu_size(self):
        parsed = self._parse(MOON_BOOT)
        self.assertEqual(parsed.name, "Moon Boot")
        self.assertEqual(parsed.brand.name, "Moon Boot")
        self.assertEqual(parsed.category.slug, "footwear")
        by_size = {variant.size: variant for variant in parsed.variants}
        self.assertEqual(set(by_size), {"S", "M", "L"})
        self.assertEqual(by_size["S"].price, Decimal("6050"))
        self.assertEqual(by_size["M"].price, Decimal("6290"))
        self.assertEqual(by_size["L"].price, Decimal("6550"))
        self.assertTrue(by_size["S"].is_available)
        self.assertTrue(by_size["M"].is_available)
        self.assertFalse(by_size["L"].is_available)
        self.assertEqual(parsed.base_price, Decimal("6050"))

    def test_title_strips_name_label_prefix(self):
        parsed = self._parse(
            "Назва: Стьобаний бомбер Massimo Dutti\n"
            "Бренд: Massimo Dutti\n\n"
            "🏷️2650 грн"
        )
        self.assertEqual(parsed.name, "Стьобаний бомбер Massimo Dutti")
        self.assertNotIn("Назва", parsed.name)

    def test_ugg_clog_matches_footwear_category(self):
        parsed = self._parse(
            "UGG Goldenstar Clog\n"
            "Бренд: UGG\n\n"
            "🏷️4050 грн"
        )
        self.assertEqual(parsed.category.slug, "footwear")

    def test_zara_jacket_trailing_uah_price_not_chest_size(self):
        parsed = self._parse(ZARA_JACKET)
        self.assertEqual(parsed.name, "Чоловіча куртка Zara (під замовлення)")
        self.assertEqual(parsed.brand.name, "Zara")
        self.assertEqual(parsed.category.slug, "outerwear")
        by_size = {variant.size: variant for variant in parsed.variants}
        self.assertEqual(set(by_size), {"S", "M", "L", "XL"})
        self.assertEqual(by_size["S"].price, Decimal("3150"))
        self.assertEqual(by_size["M"].price, Decimal("3250"))
        self.assertEqual(by_size["L"].price, Decimal("3350"))
        self.assertEqual(by_size["XL"].price, Decimal("3450"))
        self.assertEqual(parsed.base_price, Decimal("3150"))

    def test_michael_kors_bag_colors_and_prices(self):
        parsed = self._parse(MICHAEL_KORS_BAG)
        self.assertEqual(
            parsed.name,
            "Елегантна шкіряна сумка Michael Kors Pratt Medium Satchel",
        )
        self.assertEqual(parsed.brand.name, "Michael Kors")
        self.assertEqual(parsed.category.slug, "bags")
        self.assertIn("стильна модель на кожен день", parsed.description)
        self.assertIn("29 * 22 * 13", parsed.description)
        self.assertNotIn("Кольори", parsed.description)
        self.assertNotIn("5050", parsed.description)
        self.assertNotIn("М’ятна", parsed.description)
        self.assertNotIn("Бренд:", parsed.description)
        self.assertEqual(len(parsed.variants), 3)
        by_color = {variant.color: variant for variant in parsed.variants}
        self.assertEqual(set(by_color), {"Чорна", "М’ятна", "Коричнева"})
        for variant in parsed.variants:
            self.assertEqual(variant.size, "ONE SIZE")
        self.assertEqual(by_color["Чорна"].price, Decimal("5050"))
        self.assertEqual(by_color["М’ятна"].price, Decimal("4950"))
        self.assertEqual(by_color["Коричнева"].price, Decimal("4890"))
        self.assertEqual(parsed.base_price, Decimal("4890"))

    def test_zara_ski_puffer_each_size_keeps_own_price(self):
        """«• XS — ОГ 82–86 см — 🏷️ 2950 грн» — розмір із заміром і власною
        ціною на тому ж рядку не повинен ділити спільну ціну з іншими
        розмірами (регресія на баг «одна ціна на весь розмірний ряд»)."""
        parsed = self._parse(ZARA_SKI_PUFFER)
        by_size = {variant.size: variant for variant in parsed.variants}
        self.assertEqual(set(by_size), {"XS", "S", "M", "L"})
        self.assertEqual(by_size["XS"].price, Decimal("2950"))
        self.assertEqual(by_size["S"].price, Decimal("3090"))
        self.assertEqual(by_size["M"].price, Decimal("3220"))
        self.assertEqual(by_size["L"].price, Decimal("3350"))
        self.assertEqual(parsed.base_price, Decimal("2950"))

    def test_acne_longsleeve_paren_measurement_and_bare_sold_out(self):
        """«S (ПОГ 56см, ...) 🏷️5250» без тире й «L ❌Sold out» без ціни —
        обидва формати мають дати справжні розміри, а не «ONE SIZE»."""
        parsed = self._parse(ACNE_LONGSLEEVE)
        by_size = {variant.size: variant for variant in parsed.variants}
        self.assertEqual(set(by_size), {"S", "M", "L"})
        self.assertEqual(by_size["S"].price, Decimal("5250"))
        self.assertEqual(by_size["M"].price, Decimal("5350"))
        self.assertTrue(by_size["S"].is_available)
        self.assertTrue(by_size["M"].is_available)
        self.assertFalse(by_size["L"].is_available)
        self.assertNotIn("🏷️", parsed.description)
        self.assertNotIn("5250", parsed.description)

    def test_emporio_armani_bag_sets_compare_price(self):
        """«🏷️4510 ( замість 8200 )» має дати і base_price, і compare_price,
        щоб на сайті показалась закреслена стара ціна поруч з новою."""
        parsed = self._parse(EMPORIO_ARMANI_BAG)
        self.assertEqual(parsed.base_price, Decimal("4510"))
        self.assertEqual(parsed.compare_price, Decimal("8200"))
        self.assertNotIn("8200", parsed.description)
        self.assertNotIn("4510", parsed.description)

    def test_coach_grace_bag_trailing_price_not_in_description(self):
        """Гола ціна («під замовлення 🏷️6550») після абзацу опису не має
        лишатись продубльованою текстом в description."""
        parsed = self._parse(COACH_GRACE_BAG)
        self.assertEqual(parsed.base_price, Decimal("6550"))
        self.assertIn("витонченого стилю", parsed.description)
        self.assertNotIn("6550", parsed.description)
        self.assertNotIn("під замовлення", parsed.description.lower())

    def test_ray_ban_two_colors_with_stock_and_shared_price(self):
        """«зелена лінза 4 штуки» / «коричнева 2 штуки» на власних рядках,
        спільна ціна нижче — обидва кольори мають лишитись, а не
        злипатись в один варіант з "штуки" в назві кольору."""
        parsed = self._parse(RAY_BAN_TWO_COLORS)
        by_color = {v.color: v for v in parsed.variants}
        self.assertEqual(set(by_color), {"Зелена", "Коричнева"})
        self.assertEqual(by_color["Зелена"].price, Decimal("4550"))
        self.assertEqual(by_color["Зелена"].stock_qty, 4)
        self.assertEqual(by_color["Коричнева"].stock_qty, 2)

    def test_coach_slippers_named_colors_without_own_price(self):
        """«чорні , рожеві та білі в одну ціну» — кольори без власної ціни
        мають розмножити вже знайдені безколірні розмір/ціна варіанти."""
        parsed = self._parse(COACH_SLIPPERS_NAMED_COLORS)
        colors = {v.color for v in parsed.variants}
        self.assertEqual(colors, {"Чорні", "Рожеві", "Білі"})
        sizes_per_color = {
            color: {v.size for v in parsed.variants if v.color == color}
            for color in colors
        }
        for sizes in sizes_per_color.values():
            self.assertEqual(sizes, {"35", "36"})

    def test_tory_burch_slippers_size_mentioned_in_prose(self):
        """«1 в наявності 38 розмір ( 24 см )» — розмір названо в реченні,
        а не в окремому рядку-варіанті."""
        parsed = self._parse(TORY_BURCH_SLIPPERS)
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.variants[0].size, "38")
        self.assertEqual(parsed.variants[0].price, Decimal("5499"))

    def test_new_balance_availability_context_not_shared(self):
        """«В наявності» / «під замовлення» — два окремі блоки з однаковою
        ціною в одному капшені; розміри з першого блоку не повинні
        понижуватись до stock=0 через другий загальний список."""
        parsed = self._parse(NEW_BALANCE_UNDERWEAR)
        by_size = {v.size: v for v in parsed.variants}
        self.assertEqual(by_size["M"].stock_qty, 1)
        self.assertEqual(by_size["L"].stock_qty, 1)
        self.assertEqual(by_size["XL"].stock_qty, 1)
        self.assertEqual(by_size["S"].stock_qty, 0)

    def test_miu_miu_color_label_prefix_stripped(self):
        """«✨ Колір оправи: золотистий» — лейбл-префікс не має лишатись
        частиною назви кольору."""
        parsed = self._parse(MIU_MIU_GLASSES)
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.variants[0].color, "золотистий")

    def test_one_size_price_line_not_treated_as_color(self):
        """«One Size — 1290 грн» — розмір, а не назва кольору."""
        parsed = self._parse(PRL_SOCKS_ONE_SIZE)
        self.assertEqual(len(parsed.variants), 1)
        self.assertIsNone(parsed.variants[0].color)
        self.assertEqual(parsed.variants[0].size, "ONE SIZE")

    def test_pinko_bag_bare_size_header_keeps_description(self):
        """Голе «Розміри:» (без «та ціни») — фізичні виміри сумки, не
        таблиця розмір↔ціна; опис не повинен обриватись на ньому."""
        parsed = self._parse(PINKO_BAG_BARE_DIMENSIONS)
        self.assertIn("Максимальна довжина ременя", parsed.description)
        self.assertIn("Кількість кишень", parsed.description)
