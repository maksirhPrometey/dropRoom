from django.core.management import call_command
from django.test import TestCase

from src.catalog.models import Brand, Category, Product
from src.telegram_import.models import TelegramImport
from src.telegram_import.tests.test_parser import UGG_VENTURE_DAZE


class RefreshTelegramImportCopyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand, _ = Brand.objects.get_or_create(
            name="UGG",
            defaults={"slug": "ugg"},
        )
        cls.category, _ = Category.objects.get_or_create(
            slug="footwear",
            defaults={"name": "Footwear"},
        )
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
