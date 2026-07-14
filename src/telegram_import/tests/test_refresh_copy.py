from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from src.catalog.models import Brand, Category, Product, ProductVariant
from src.telegram_import.models import TelegramImport
from src.telegram_import.tests.test_parser import MICHAEL_KORS_BAG, UGG_VENTURE_DAZE


class RefreshTelegramImportCopyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand, _ = Brand.objects.get_or_create(
            name="UGG",
            defaults={"slug": "ugg"},
        )
        Brand.objects.get_or_create(
            name="Michael Kors",
            defaults={"slug": "michael-kors"},
        )
        Brand.objects.get_or_create(name="Crocs", defaults={"slug": "crocs"})
        cls.category, _ = Category.objects.get_or_create(
            slug="footwear",
            defaults={"name": "Footwear"},
        )
        Category.objects.get_or_create(slug="bags", defaults={"name": "Bags"})
        cls.product = Product.objects.create(
            brand=cls.brand,
            category=cls.category,
            name=UGG_VENTURE_DAZE.split(" — ", 1)[0]
            + " — "
            + UGG_VENTURE_DAZE.split(" — ", 1)[1][:200],
            description="📏 Розміри та ціни:\n🔹 34 (21,5 см) — 3 850 грн",
            base_price=3850,
            gender="U",
        )
        cls.import_record = TelegramImport.objects.create(
            channel_id=-5566899151,
            message_id=113313,
            raw_caption=UGG_VENTURE_DAZE,
            status=TelegramImport.STATUS_IMPORTED,
            product=cls.product,
        )

    def test_refresh_updates_name_and_description(self):
        call_command("refresh_telegram_import_copy", message_id=113313)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "UGG Venture Daze")
        self.assertIn("стильні сандалі", self.product.description)
        self.assertNotIn("Розміри та ціни", self.product.description)

    def test_dry_run_keeps_database(self):
        before_name = self.product.name
        call_command(
            "refresh_telegram_import_copy",
            message_id=113313,
            dry_run=True,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, before_name)

    def test_refresh_resyncs_color_price_variants(self):
        brand = Brand.objects.get(slug="michael-kors")
        bags = Category.objects.get(slug="bags")
        product = Product.objects.create(
            brand=brand,
            category=bags,
            name="MK bag wrong",
            description=(
                "стиль\nКольори та ціни:\n🖤 Чорна — 🏷️ 5050 грн"
            ),
            base_price=Decimal("1000"),
            gender="U",
            slug="mk-bag-refresh-test",
        )
        ProductVariant.objects.create(
            product=product,
            size="ONE SIZE",
            sku="TG-test-mk-onesize",
            price=Decimal("4890"),
            stock_qty=0,
            is_available=True,
        )
        TelegramImport.objects.create(
            channel_id=-5566899151,
            message_id=999001,
            raw_caption=MICHAEL_KORS_BAG,
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )

        call_command("refresh_telegram_import_copy", message_id=999001)

        product.refresh_from_db()
        self.assertNotIn("Кольори", product.description)
        self.assertIn("29 * 22 * 13", product.description)
        variants = list(product.variants.select_related("color"))
        self.assertEqual(len(variants), 3)
        colors = {v.color.name for v in variants}
        self.assertEqual(colors, {"Чорна", "М’ятна", "Коричнева"})
