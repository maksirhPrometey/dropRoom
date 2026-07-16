from decimal import Decimal

from django import forms


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ("CARD", "Картка"),
        ("CASH", "При отриманні"),
    ]
    DELIVERY_CHOICES = [
        ("nova_poshta", "Нова Пошта"),
    ]

    FREE_DELIVERY_THRESHOLD = Decimal("3000")
    NOVA_POSHTA_COST = Decimal("110")

    first_name = forms.CharField(
        max_length=100,
        label="Ім'я",
        widget=forms.TextInput(attrs={"placeholder": "Олена"}),
    )
    last_name = forms.CharField(
        max_length=100,
        label="Прізвище",
        widget=forms.TextInput(attrs={"placeholder": "Кравець"}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "email@example.com"}),
    )
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        widget=forms.TextInput(attrs={"placeholder": "+380", "inputmode": "tel"}),
    )
    delivery_method = forms.ChoiceField(
        choices=DELIVERY_CHOICES,
        initial="nova_poshta",
        widget=forms.RadioSelect,
    )
    delivery_address = forms.CharField(
        max_length=500,
        label="Адреса або відділення НП",
        widget=forms.TextInput(attrs={"placeholder": "Місто, відділення НП або адреса"}),
    )
    comment = forms.CharField(
        required=False,
        label="Коментар до замовлення",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Будь-яка додаткова інформація"}),
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        initial="CARD",
        label="Спосіб оплати",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
            profile = getattr(user, "profile", None)
            if profile and profile.phone:
                self.fields["phone"].initial = profile.phone

    @classmethod
    def delivery_cost_for(cls, subtotal: Decimal, delivery_method: str) -> Decimal:
        if subtotal >= cls.FREE_DELIVERY_THRESHOLD:
            return Decimal("0")
        return cls.NOVA_POSHTA_COST

    @classmethod
    def order_total_for(
        cls, subtotal: Decimal, discount: Decimal, delivery_method: str
    ) -> Decimal:
        delivery = cls.delivery_cost_for(subtotal, delivery_method)
        return subtotal - discount + delivery

    def delivery_cost(self) -> Decimal:
        subtotal = self.cleaned_data.get("_subtotal", Decimal("0"))
        return self.delivery_cost_for(
            subtotal, self.cleaned_data.get("delivery_method", "nova_poshta")
        )

    def order_total(self) -> Decimal:
        subtotal = self.cleaned_data.get("_subtotal", Decimal("0"))
        discount = self.cleaned_data.get("_discount", Decimal("0"))
        return self.order_total_for(
            subtotal,
            discount,
            self.cleaned_data.get("delivery_method", "nova_poshta"),
        )

    def bind_cart_totals(self, subtotal: Decimal, discount: Decimal) -> None:
        """Зберігає суми кошика для розрахунку доставки в clean()."""
        self._cart_subtotal = subtotal
        self._cart_discount = discount

    def clean(self):
        cleaned = super().clean()
        subtotal = getattr(self, "_cart_subtotal", Decimal("0"))
        discount = getattr(self, "_cart_discount", Decimal("0"))
        cleaned["_subtotal"] = subtotal
        cleaned["_discount"] = discount
        return cleaned

    def delivery_label(self) -> str:
        method = self.cleaned_data.get("delivery_method", "nova_poshta")
        return dict(self.DELIVERY_CHOICES).get(method, method)
