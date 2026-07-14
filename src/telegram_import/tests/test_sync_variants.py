from decimal import Decimal

from django.test import TestCase

from src.catalog.models import Brand, Category, Product, ProductVariant
from src.telegram_import.services.importer import _sync_variants
from src.telegram_import.services.parser_types import ParsedVariant


class SyncVariantsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        brand, _ = Brand.objects.get_or_create(
            slug="zara", defaults={"name": "Zara", "is_active": True}
        )
        category, _ = Category.objects.get_or_create(
            slug="outerwear", defaults={"name": "Outerwear"}
        )
        cls.product = Product.objects.create(
            brand=brand,
            category=category,
            name="Jacket",
            slug="zara-jacket-test",
            base_price=Decimal("46"),
            gender="M",
            is_active=True,
        )
        # Старий SKU як на проді: подвійний дефіс + пробіл у size.
        ProductVariant.objects.create(
            product=cls.product,
            size="ONE SIZE",
            sku="TG--5566899151-222-default-ONE SIZE",
            price=Decimal("46"),
            stock_qty=0,
            is_available=True,
        )

    def test_sync_updates_legacy_sku_without_unique_violation(self):
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=222,
            parsed_variants=[
                ParsedVariant(
                    size="ONE SIZE",
                    price=Decimal("2999"),
                    stock_qty=0,
                    is_available=True,
                )
            ],
            default_price=Decimal("1000"),
        )
        self.product.refresh_from_db()
        variants = list(self.product.variants.all())
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].price, Decimal("2999"))
        self.assertEqual(self.product.base_price, Decimal("2999"))
        self.assertNotEqual(
            variants[0].sku, "TG--5566899151-222-default-ONE SIZE"
        )

    def test_sync_replaces_one_size_with_letter_sizes(self):
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=222,
            parsed_variants=[
                ParsedVariant(size="S", price=Decimal("3150"), stock_qty=0),
                ParsedVariant(size="M", price=Decimal("3250"), stock_qty=0),
            ],
            default_price=Decimal("1000"),
        )
        sizes = set(self.product.variants.values_list("size", flat=True))
        self.assertEqual(sizes, {"S", "M"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("3150"))
