from django.contrib import admin
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from config.admin_utils import DropRoomModelAdmin

from .models import Cart, CartItem, Order, OrderItem, PromoCode


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    fields = ["variant", "quantity", "display_line_total", "added_at"]
    readonly_fields = ["display_line_total", "added_at"]
    autocomplete_fields = ["variant"]

    @admin.display(description="Сума")
    def display_line_total(self, obj):
        if not obj.pk:
            return "—"
        return f"{obj.line_total} ₴"


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    fields = [
        "variant",
        "name_snapshot",
        "brand_snapshot",
        "price_snapshot",
        "quantity",
        "display_line_total",
    ]
    readonly_fields = ["display_line_total"]
    autocomplete_fields = ["variant"]

    @admin.display(description="Сума")
    def display_line_total(self, obj):
        if not obj.pk:
            return "—"
        return f"{obj.line_total} ₴"


@admin.register(PromoCode)
class PromoCodeAdmin(DropRoomModelAdmin):
    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "brand",
        "uses_count",
        "max_uses",
        "valid_from",
        "valid_until",
        "is_active",
    ]
    list_filter = [
        ("discount_type", ChoicesDropdownFilter),
        ("is_active", ChoicesDropdownFilter),
        ("brand", RelatedDropdownFilter),
    ]
    search_fields = ["code"]
    autocomplete_fields = ["brand"]
    fieldsets = [
        ("Код", {"fields": ["code", "is_active"]}),
        (
            "Знижка",
            {"fields": ["discount_type", "discount_value", "brand", "min_order"]},
        ),
        ("Ліміти", {"fields": ["max_uses", "uses_count"]}),
        ("Період", {"fields": ["valid_from", "valid_until"]}),
    ]


@admin.register(Cart)
class CartAdmin(DropRoomModelAdmin):
    list_display = [
        "__str__",
        "user",
        "promo",
        "display_item_count",
        "display_subtotal",
        "updated_at",
    ]
    list_filter = [("promo", RelatedDropdownFilter)]
    search_fields = ["user__username", "user__email", "session_key"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "display_subtotal",
        "display_discount",
        "display_total",
    ]
    autocomplete_fields = ["user", "promo"]
    inlines = [CartItemInline]
    fieldsets = [
        ("Власник", {"fields": ["user", "session_key", "promo"]}),
        (
            "Підсумки",
            {
                "fields": [
                    "display_subtotal",
                    "display_discount",
                    "display_total",
                ],
            },
        ),
        ("Дати", {"fields": ["created_at", "updated_at"]}),
    ]

    @admin.display(description="Позицій")
    def display_item_count(self, obj):
        return obj.get_item_count()

    @admin.display(description="Сума")
    def display_subtotal(self, obj):
        return f"{obj.get_subtotal()} ₴"

    @admin.display(description="Знижка")
    def display_discount(self, obj):
        return f"{obj.get_discount()} ₴"

    @admin.display(description="Разом")
    def display_total(self, obj):
        return f"{obj.get_total()} ₴"


@admin.register(Order)
class OrderAdmin(DropRoomModelAdmin):
    list_display = [
        "id",
        "user",
        "status",
        "payment_method",
        "total",
        "created_at",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("payment_method", ChoicesDropdownFilter),
        "created_at",
    ]
    search_fields = ["user__username", "user__email", "id"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["user", "address", "promo"]
    inlines = [OrderItemInline]
    fieldsets = [
        (
            "Клієнт",
            {"fields": ["user", "address", "notes"]},
        ),
        (
            "Статус і оплата",
            {"fields": ["status", "payment_method", "promo"]},
        ),
        (
            "Суми",
            {
                "fields": [
                    "subtotal",
                    "discount_amount",
                    "delivery_cost",
                    "total",
                ],
            },
        ),
        ("Дати", {"fields": ["created_at", "updated_at"]}),
    ]
    ordering = ["-created_at"]
