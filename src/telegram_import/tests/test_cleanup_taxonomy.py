from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from src.catalog.models import Brand, Category, Product
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.parser import _match_category


class CleanupTelegramTaxonomyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.crocs, _ = Brand.objects.get_or_create(
            slug="crocs",
            defaults={"name": "Crocs", "is_active": True},
        )
        cls.sandro_brand, _ = Brand.objects.get_or_create(
            slug="sandro",
            defaults={"name": "Sandro", "is_active": True},
        )
        cls.bags, _ = Category.objects.get_or_create(
            slug="bags",
            defaults={"name": "Bags"},
        )
        cls.sneakers, _ = Category.objects.get_or_create(
            slug="sneakers",
            defaults={"name": "Sneakers"},
        )
        # помилкова категорія-бренд
        cls.sandro_cat, _ = Category.objects.get_or_create(
            slug="sandro",
            defaults={"name": "Sandro"},
        )

    def test_match_category_backpack_to_bags(self):
        category = _match_category("Стильний нейлоновий рюкзак у бежевому кольорі")
        self.assertIsNotNone(category)
        self.assertEqual(category.slug, "bags")

    def test_match_category_ignores_brand_named_category(self):
        # Caption згадує Sandro — але Category sandro = bogus, має виграти bags
        category = _match_category(
            "Рюкзак Sandro\n\nНейлоновий рюкзак\n🏷️3150"
        )
        self.assertEqual(category.slug, "bags")

    def test_cleanup_moves_and_deletes_bogus_category(self):
        product = Product.objects.create(
            brand=self.crocs,
            category=self.sandro_cat,
            name="Стильний нейлоновий рюкзак у бежевому кольорі",
            slug="nylon-backpack-beige",
            base_price=Decimal("3150"),
            gender="U",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-1,
            message_id=117359,
            raw_caption="Стильний нейлоновий рюкзак у бежевому кольорі 🤍\n\n🏷️3150",
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )

        out = StringIO()
        call_command("cleanup_telegram_taxonomy", stdout=out)
        product.refresh_from_db()
        self.assertEqual(product.category.slug, "bags")
        self.assertFalse(Category.objects.filter(slug="sandro", name="Sandro").exists())
        self.assertTrue(Brand.objects.filter(slug="sandro").exists())
        self.assertIn("переміщено", out.getvalue())

    def test_deactivate_no_brand(self):
        product = Product.objects.create(
            brand=self.crocs,
            category=self.bags,
            name="Невідома річ",
            slug="unknown-thing",
            base_price=Decimal("100"),
            gender="U",
            is_active=True,
        )
        TelegramImport.objects.create(
            channel_id=-1,
            message_id=1,
            raw_caption="Невідома річ без бренду\n🏷️100",
            status=TelegramImport.STATUS_IMPORTED,
            product=product,
        )
        call_command("cleanup_telegram_taxonomy", "--deactivate-no-brand")
        product.refresh_from_db()
        self.assertFalse(product.is_active)
