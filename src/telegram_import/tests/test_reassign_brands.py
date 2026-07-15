from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from src.catalog.models import Brand, Category, Product
from src.telegram_import.models import TelegramImport


class ReassignProductBrandsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.crocs, _ = Brand.objects.get_or_create(
            slug="crocs",
            defaults={"name": "Crocs", "is_active": True},
        )
        cls.bags, _ = Category.objects.get_or_create(
            slug="bags",
            defaults={"name": "Bags"},
        )
        cls.sneakers, _ = Category.objects.get_or_create(
            slug="sneakers",
            defaults={"name": "Sneakers"},
        )

    def test_gant_sneakers_leave_crocs(self):
        product = Product.objects.create(
            brand=self.crocs,
            category=self.sneakers,
            name="Кросівки GANT 💖",
            slug="gant-sneakers",
            base_price=Decimal("1999"),
            gender="U",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-1,
            message_id=26,
            raw_caption="Кросівки GANT 💖\n\n🏷️1999",
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )

        out = StringIO()
        call_command("reassign_product_brands", stdout=out)
        product.refresh_from_db()
        self.assertEqual(product.brand.slug, "gant")
        self.assertEqual(product.brand.name, "GANT")

    def test_crocs_without_mention_becomes_unbranded(self):
        product = Product.objects.create(
            brand=self.crocs,
            category=self.bags,
            name="Стильний нейлоновий рюкзак у бежевому кольорі",
            slug="nylon-pack",
            base_price=Decimal("3150"),
            gender="U",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-1,
            message_id=25,
            raw_caption="Стильний нейлоновий рюкзак у бежевому кольорі\n🏷️3150",
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )
        call_command("reassign_product_brands")
        product.refresh_from_db()
        self.assertEqual(product.brand.slug, "unbranded")
