from django import forms

TOPIC_CHOICES = [
    ("order", "Замовлення"),
    ("styling", "Підбір"),
    ("delivery", "Доставка"),
    ("return", "Повернення"),
    ("collab", "Колаборація"),
    ("other", "Інше"),
]


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Ім'я",
        widget=forms.TextInput(attrs={"placeholder": "Олена Кравець"}),
    )
    contact = forms.CharField(
        max_length=200,
        label="Телефон або email",
        widget=forms.TextInput(attrs={"placeholder": "+380 / @ / email"}),
    )
    topic = forms.ChoiceField(
        choices=TOPIC_CHOICES,
        label="Тема",
        widget=forms.RadioSelect,
        initial="styling",
    )
    brand = forms.CharField(
        max_length=100,
        required=False,
        label="Бренд (опціонально)",
        widget=forms.TextInput(attrs={"placeholder": "Nike, Acne Studios…"}),
    )
    message = forms.CharField(
        label="Повідомлення",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Що шукаєте? Який стиль? Який бюджет? Розповідайте.",
                "rows": 5,
            }
        ),
    )
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"tabindex": "-1", "aria-hidden": "true"}),
    )

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value
