from decimal import Decimal

from django.test import Client, TestCase

from src.catalog.models import Brand, Category, Product


class CatalogSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        brand = Brand.objects.create(name="Lacoste", slug="lacoste", is_active=True)
        other = Brand.objects.create(name="Crocs", slug="crocs", is_active=True)
        category = Category.objects.create(name="Bags", slug="bags")
        Product.objects.create(
            brand=brand,
            category=category,
            name="Сумка-шопер Lacoste L.12.12",
            slug="lacoste-shopper",
            subtitle="Shopper",
            base_price=Decimal("3450"),
            is_active=True,
        )
        Product.objects.create(
            brand=other,
            category=category,
            name="Classic Clog",
            slug="classic-clog",
            base_price=Decimal("2200"),
            is_active=True,
        )

    def setUp(self):
        self.client = Client()

    def test_search_by_name(self):
        response = self.client.get("/catalog/", {"q": "шопер"})
        self.assertEqual(response.status_code, 200)
        products = list(response.context["products"])
        self.assertEqual(len(products), 1)
        self.assertIn("Lacoste", products[0].name)

    def test_search_by_brand(self):
        response = self.client.get("/catalog/", {"q": "crocs"})
        self.assertEqual(response.status_code, 200)
        products = list(response.context["products"])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].slug, "classic-clog")

    def test_htmx_returns_partial(self):
        response = self.client.get(
            "/catalog/",
            {"q": "lacoste"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/partials/product_results.html")
        self.assertContains(response, "Сумка-шопер Lacoste")
        self.assertContains(response, "Знайдено")
