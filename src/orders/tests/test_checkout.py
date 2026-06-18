from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from src.catalog.models import Brand, Category, Product, ProductVariant
from src.orders.forms import CheckoutForm
from src.orders.models import Cart, CartItem, Order
from src.orders.utils import get_or_create_cart


class CheckoutFormTests(TestCase):
    def test_delivery_cost_nova_poshta_below_threshold(self):
        cost = CheckoutForm.delivery_cost_for(Decimal("500"), "nova_poshta")
        self.assertEqual(cost, Decimal("110"))

    def test_delivery_cost_free_above_threshold(self):
        cost = CheckoutForm.delivery_cost_for(Decimal("3000"), "nova_poshta")
        self.assertEqual(cost, Decimal("0"))

    def test_payment_method_rejects_invalid_value(self):
        form = CheckoutForm(
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "t@example.com",
                "phone": "+380501234567",
                "delivery_method": "nova_poshta",
                "delivery_address": "Київ, НП 1",
                "payment_method": "cod",
            }
        )
        form.bind_cart_totals(Decimal("1000"), Decimal("0"))
        self.assertFalse(form.is_valid())
        self.assertIn("payment_method", form.errors)

    def test_payment_method_accepts_card_and_cash(self):
        for method in ("CARD", "CASH"):
            form = CheckoutForm(
                {
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "t@example.com",
                    "phone": "+380501234567",
                    "delivery_method": "pickup",
                    "delivery_address": "Київ",
                    "payment_method": method,
                }
            )
            form.bind_cart_totals(Decimal("1000"), Decimal("0"))
            self.assertTrue(form.is_valid(), form.errors)


class CheckoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="pass12345"
        )
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Tops", slug="tops")
        self.product = Product.objects.create(
            brand=self.brand,
            category=self.category,
            name="Hoodie",
            slug="hoodie",
            base_price=Decimal("1500"),
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="M",
            sku="HOODIE-M",
            price=Decimal("1500"),
            stock_qty=5,
            is_available=True,
        )
        self.client = Client()
        self.client.login(username="buyer", password="pass12345")

    def _add_to_cart(self):
        session = self.client.session
        session.save()
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)

    def test_checkout_post_creates_order(self):
        self._add_to_cart()
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "first_name": "Олена",
                "last_name": "Кравець",
                "email": "buyer@example.com",
                "phone": "+380501234567",
                "delivery_method": "nova_poshta",
                "delivery_address": "Київ, НП 12",
                "payment_method": "CARD",
                "comment": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:profile"))
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, "CARD")
        self.assertEqual(order.delivery_cost, Decimal("110"))
        self.assertEqual(order.total, Decimal("1610"))
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())

    def test_checkout_post_invalid_payment_does_not_create_order(self):
        self._add_to_cart()
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "first_name": "Олена",
                "last_name": "Кравець",
                "email": "buyer@example.com",
                "phone": "+380501234567",
                "delivery_method": "nova_poshta",
                "delivery_address": "Київ, НП 12",
                "payment_method": "card",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, "payment_method")
