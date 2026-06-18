from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [("PERCENT", "Відсоток"), ("FIXED", "Фіксована сума")]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    brand = models.ForeignKey(
        "catalog.Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_codes",
    )
    min_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоди"

    def __str__(self) -> str:
        return self.code

    def is_valid(self, order_total=0) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        if order_total < self.min_order:
            return False
        return True

    def calculate_discount(self, subtotal) -> "Decimal":
        from decimal import Decimal

        if self.discount_type == "PERCENT":
            return (subtotal * self.discount_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        return min(self.discount_value, subtotal)


class Cart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(max_length=64, blank=True)
    promo = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Кошик"
        verbose_name_plural = "Кошики"

    def __str__(self) -> str:
        if self.user:
            return f"Кошик {self.user.username}"
        return f"Кошик (анонім {self.session_key[:8]})"

    def get_subtotal(self):
        from decimal import Decimal

        return sum(
            item.variant.price * item.quantity for item in self.items.all()
        )

    def get_discount(self):
        from decimal import Decimal

        subtotal = self.get_subtotal()
        if self.promo and self.promo.is_valid(subtotal):
            return self.promo.calculate_discount(subtotal)
        return Decimal("0")

    def get_total(self):
        return self.get_subtotal() - self.get_discount()

    def get_item_count(self) -> int:
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")
        verbose_name = "Позиція кошика"
        verbose_name_plural = "Позиції кошика"

    def __str__(self) -> str:
        return f"{self.variant} x{self.quantity}"

    @property
    def line_total(self):
        return self.variant.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Очікує"),
        ("PAID", "Оплачено"),
        ("SHIPPED", "Відправлено"),
        ("DONE", "Виконано"),
        ("CANCELLED", "Скасовано"),
    ]
    PAYMENT_CHOICES = [
        ("CARD", "Картка"),
        ("APPLE_PAY", "Apple Pay"),
        ("GPAY", "Google Pay"),
        ("CASH", "Готівка"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    promo = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default="CARD"
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"

    def __str__(self) -> str:
        return f"Замовлення #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )
    name_snapshot = models.CharField(max_length=255)
    brand_snapshot = models.CharField(max_length=100)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Позиція замовлення"
        verbose_name_plural = "Позиції замовлення"

    def __str__(self) -> str:
        return f"{self.name_snapshot} x{self.quantity}"

    @property
    def line_total(self):
        return self.price_snapshot * self.quantity
