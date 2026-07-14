from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from src.catalog.models import Brand, Category, Product
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.parser import resolve_brand


class FixTelegramBrandsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.crocs, _ = Brand.objects.get_or_create(
            slug="crocs",
            defaults={"name": "Crocs", "is_active": True},
        )
        cls.katy, _ = Brand.objects.get_or_create(
            slug="katy-perry",
            defaults={"name": "Katy Perry", "is_active": True},
        )
        category, _ = Category.objects.get_or_create(
            slug="footwear",
            defaults={"name": "Footwear"},
        )
        cls.product = Product.objects.create(
            brand=cls.crocs,
            category=category,
            name="Босоніжки Katy Perry",
            slug="katy-perry-sandals",
            base_price=Decimal("999"),
            gender="W",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-5566899151,
            message_id=9001,
            raw_caption="Босоніжки Katy Perry\nБренд: Katy Perry\n\n🏷️999 грн",
            status=TelegramImport.STATUS_IMPORTED,
            product=cls.product,
        )

    def test_resolve_brand_from_label_and_name(self):
        brand = resolve_brand("Босоніжки Katy Perry\nБренд: Katy Perry")
        self.assertEqual(brand.name, "Katy Perry")

    def test_fix_command_updates_default_brand(self):
        out = StringIO()
        call_command(
            "fix_telegram_brands",
            "--only-default",
            stdout=out,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.brand_id, self.katy.pk)
        self.assertIn("Katy Perry", out.getvalue())

    def test_create_missing_brand_from_label(self):
        Brand.objects.filter(slug="unknown-label").delete()
        product = Product.objects.create(
            brand=self.crocs,
            category=self.product.category,
            name="Test Bag",
            slug="unknown-brand-bag",
            base_price=Decimal("1000"),
            gender="U",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-5566899151,
            message_id=9002,
            raw_caption="Сумка\nБренд: Unknown Label\n🏷️2000 грн",
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )
        call_command("fix_telegram_brands", "--create-missing", "--slug", product.slug)
        product.refresh_from_db()
        self.assertEqual(product.brand.name, "Unknown Label")
