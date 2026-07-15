from decimal import Decimal

from django.test import TestCase

from src.catalog.models import Brand, Category, Product


class ProductDisplayBrandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gant, _ = Brand.objects.get_or_create(
            slug="gant",
            defaults={"name": "GANT", "is_active": True},
        )
        cls.crocs, _ = Brand.objects.get_or_create(
            slug="crocs",
            defaults={"name": "Crocs", "is_active": True},
        )
        cls.unbranded, _ = Brand.objects.get_or_create(
            slug="unbranded",
            defaults={"name": "Без бренду", "is_active": True},
        )
        cls.cat, _ = Category.objects.get_or_create(
            slug="sneakers",
            defaults={"name": "Sneakers"},
        )

    def test_real_brand_display(self):
        product = Product.objects.create(
            brand=self.gant,
            category=self.cat,
            name="Кросівки GANT",
            slug="gant-1",
            base_price=Decimal("1999"),
            gender="U",
        )
        self.assertTrue(product.has_real_brand)
        self.assertEqual(product.display_brand, "GANT")

    def test_crocs_fallback_shows_product_name(self):
        product = Product.objects.create(
            brand=self.crocs,
            category=self.cat,
            name="Кросівки GANT 💖",
            slug="gant-2",
            base_price=Decimal("1999"),
            gender="U",
        )
        self.assertFalse(product.has_real_brand)
        self.assertEqual(product.display_brand, "Кросівки GANT 💖")

    def test_unbranded_shows_product_name(self):
        product = Product.objects.create(
            brand=self.unbranded,
            category=self.cat,
            name="Стильний нейлоновий рюкзак",
            slug="pack-1",
            base_price=Decimal("3150"),
            gender="U",
        )
        self.assertEqual(product.display_brand, "Стильний нейлоновий рюкзак")
