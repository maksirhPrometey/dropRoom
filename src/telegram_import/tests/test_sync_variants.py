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

    def test_sync_ignores_zero_sold_out_for_base_price(self):
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=222,
            parsed_variants=[
                ParsedVariant(
                    size="XS",
                    price=Decimal("0"),
                    stock_qty=0,
                    is_available=False,
                ),
                ParsedVariant(
                    size="S",
                    price=Decimal("5450"),
                    stock_qty=0,
                    is_available=True,
                ),
                ParsedVariant(
                    size="M",
                    price=Decimal("4899"),
                    stock_qty=0,
                    is_available=True,
                ),
            ],
            default_price=Decimal("1000"),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("4899"))

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

    def test_sync_keeps_separate_one_size_colors(self):
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=333,
            parsed_variants=[
                ParsedVariant(
                    size="ONE SIZE",
                    price=Decimal("5050"),
                    color="Чорна",
                    stock_qty=0,
                ),
                ParsedVariant(
                    size="ONE SIZE",
                    price=Decimal("4950"),
                    color="М’ятна",
                    stock_qty=0,
                ),
                ParsedVariant(
                    size="ONE SIZE",
                    price=Decimal("4890"),
                    color="Коричнева",
                    stock_qty=0,
                ),
            ],
            default_price=Decimal("1000"),
        )
        variants = list(self.product.variants.select_related("color"))
        self.assertEqual(len(variants), 3)
        by_color = {v.color.name: v for v in variants}
        self.assertEqual(set(by_color), {"Чорна", "М’ятна", "Коричнева"})
        self.assertEqual(by_color["Чорна"].price, Decimal("5050"))
        self.assertEqual(by_color["М’ятна"].price, Decimal("4950"))
        self.assertEqual(by_color["Коричнева"].price, Decimal("4890"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("4890"))

    def test_sync_sets_compare_price_from_old_price(self):
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=444,
            parsed_variants=[
                ParsedVariant(
                    size="ONE SIZE",
                    price=Decimal("4510"),
                    compare_price=Decimal("8200"),
                    stock_qty=0,
                ),
            ],
            default_price=Decimal("1000"),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("4510"))
        self.assertEqual(self.product.compare_price, Decimal("8200"))

    def test_sync_clears_compare_price_when_no_longer_discounted(self):
        self.product.compare_price = Decimal("8200")
        self.product.save(update_fields=["compare_price"])
        _sync_variants(
            self.product,
            channel_id=-5566899151,
            message_id=444,
            parsed_variants=[
                ParsedVariant(size="ONE SIZE", price=Decimal("4510"), stock_qty=0),
            ],
            default_price=Decimal("1000"),
        )
        self.product.refresh_from_db()
        self.assertIsNone(self.product.compare_price)
