from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
)

from config.admin_utils import DropRoomModelAdmin, image_preview

from .models import Brand, Category, Color, Drop, Product, ProductImage, ProductVariant


class LowStockFilter(SimpleListFilter):
    title = "Статус складу"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [
            ("ok", "✓ В наявності (> 5 шт)"),
            ("low", "⚠ Мало (1–5 шт)"),
            ("preorder", "↻ Під замовлення (0 шт, доступно)"),
            ("off", "✕ Недоступний"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "ok":
            return queryset.filter(stock_qty__gt=5, is_available=True)
        if self.value() == "low":
            return queryset.filter(stock_qty__gt=0, stock_qty__lte=5, is_available=True)
        if self.value() == "preorder":
            return queryset.filter(stock_qty=0, is_available=True)
        if self.value() == "off":
            return queryset.filter(is_available=False)
        return queryset


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt", "is_primary", "sort_order"]
    ordering = ["sort_order"]


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    fields = ["size", "color", "sku", "price", "stock_qty", "is_available"]
    autocomplete_fields = ["color"]


@admin.register(Brand)
class BrandAdmin(DropRoomModelAdmin):
    list_display = ["logo_thumb", "name", "country", "is_active"]
    list_filter = [("is_active", ChoicesDropdownFilter)]
    list_editable = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["logo_preview"]
    fields = ["name", "slug", "country", "logo", "logo_preview", "is_active"]

    logo_preview = image_preview("logo", width=120, height=120)

    @admin.display(description="Лого")
    def logo_thumb(self, obj):
        return self.logo_preview(obj)


@admin.register(Category)
class CategoryAdmin(DropRoomModelAdmin):
    list_display = [
        "thumb",
        "name",
        "parent",
        "show_on_home",
        "home_layout",
        "sort_order",
        "is_featured",
    ]
    list_filter = [
        ("parent", RelatedDropdownFilter),
        ("show_on_home", ChoicesDropdownFilter),
        ("is_featured", ChoicesDropdownFilter),
        ("home_layout", ChoicesDropdownFilter),
    ]
    list_editable = ["show_on_home", "sort_order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["sort_order", "name"]
    autocomplete_fields = ["parent"]
    readonly_fields = ["image_preview"]
    fieldsets = [
        (
            "Основне",
            {"fields": ["name", "slug", "parent", "sort_order", "is_featured"]},
        ),
        (
            "Головна — «Категорії / сезону»",
            {
                "fields": [
                    "show_on_home",
                    "image",
                    "image_preview",
                    "home_layout",
                    "home_variant",
                    "home_tag",
                ],
                "description": (
                    "Увімкніть «Показувати на головній» і завантажте фото. "
                    "На головній відображається до 6 категорій без батька (верхній рівень)."
                ),
            },
        ),
    ]

    image_preview = image_preview("image", width=160, height=100)

    @admin.display(description="Фото")
    def thumb(self, obj):
        return self.image_preview(obj)


@admin.register(Color)
class ColorAdmin(DropRoomModelAdmin):
    list_display = ["swatch", "name", "hex_code", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Зразок")
    def swatch(self, obj):
        from django.utils.html import format_html

        return format_html(
            '<span class="admin-color-swatch" style="background:{};"></span>',
            obj.hex_code,
        )


@admin.register(Drop)
class DropAdmin(DropRoomModelAdmin):
    list_display = [
        "cover_thumb",
        "number",
        "title",
        "season",
        "year",
        "is_live",
        "scheduled_at",
    ]
    list_filter = [
        ("is_live", ChoicesDropdownFilter),
        "season",
        "year",
    ]
    list_editable = ["is_live"]
    search_fields = ["title", "theme"]
    ordering = ["-number"]
    readonly_fields = ["cover_preview"]
    fieldsets = [
        (
            "Основне",
            {"fields": ["number", "title", "theme", "season", "year", "is_live"]},
        ),
        ("Реліз", {"fields": ["scheduled_at", "cover_image", "cover_preview"]}),
    ]

    cover_preview = image_preview("cover_image", width=200, height=120)

    @admin.display(description="Обкладинка")
    def cover_thumb(self, obj):
        return self.cover_preview(obj)


@admin.register(Product)
class ProductAdmin(DropRoomModelAdmin):
    list_display = [
        "thumb",
        "name",
        "brand",
        "category",
        "price_display",
        "total_stock_display",
        "drop",
        "is_active",
    ]
    list_filter = [
        ("brand", RelatedDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("drop", RelatedDropdownFilter),
        ("gender", ChoicesDropdownFilter),
        ("is_active", ChoicesDropdownFilter),
    ]
    search_fields = ["name", "slug", "brand__name", "subtitle"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["brand", "category", "drop"]
    readonly_fields = ["created_at", "primary_preview"]
    inlines = [ProductImageInline, ProductVariantInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("variants")

    @admin.display(description="Ціна", ordering="base_price")
    def price_display(self, obj):
        if obj.compare_price and obj.compare_price > obj.base_price:
            pct = round((1 - obj.base_price / obj.compare_price) * 100)
            return format_html(
                '<span style="font-family:monospace;">'
                '<s style="color:#999;font-size:11px;">{} ₴</s> '
                '<strong style="color:var(--accent-admin, #d28243);">{} ₴</strong> '
                '<span style="font-size:10px;background:#0a0a0a;color:#d28243;'
                'padding:2px 5px;font-weight:700;">-{}%</span>'
                "</span>",
                obj.compare_price,
                obj.base_price,
                pct,
            )
        return format_html(
            '<span style="font-family:monospace;">{} ₴</span>', obj.base_price
        )

    @admin.display(description="Склад")
    def total_stock_display(self, obj):
        avail = [v for v in obj.variants.all() if v.is_available]
        if not avail:
            return format_html(
                '<span style="font-family:monospace;color:#888;">— н/д</span>'
            )
        total = sum(v.stock_qty for v in avail)
        if total == 0:
            return format_html(
                '<span style="font-family:monospace;font-weight:700;color:#5b7fd4;">↻ Під замовлення</span>'
            )
        low = any(0 < v.stock_qty <= 5 for v in avail)
        color = "#c45a14" if low else "#1c8551"
        icon = "⚠" if low else "✓"
        return format_html(
            '<span style="font-family:monospace;font-weight:700;font-size:13px;color:{};">'
            "{} {} шт</span>",
            color, icon, total,
        )
    fieldsets = [
        (
            "Основне",
            {
                "fields": [
                    "name",
                    "slug",
                    "subtitle",
                    "brand",
                    "category",
                    "drop",
                    "gender",
                    "is_active",
                ]
            },
        ),
        ("Опис", {"fields": ["description", "material"]}),
        (
            "Ціна",
            {
                "fields": ["base_price", "compare_price"],
                "description": (
                    "Щоб показати знижку — заповніть «Стару ціну». "
                    "На сайті вона з'явиться перекресленою поруч з актуальною, "
                    "а на картці товару — бейдж з відсотком знижки."
                ),
            },
        ),
        ("Системне", {"fields": ["created_at"]}),
    ]

    @admin.display(description="Фото")
    def thumb(self, obj):
        primary = obj.images.filter(is_primary=True).first() or obj.images.first()
        if not primary or not primary.image:
            return "—"
        from django.utils.html import format_html

        return format_html(
            '<img src="{}" width="48" height="60" '
            'style="object-fit:cover;border-radius:2px;" alt="" />',
            primary.image.url,
        )

    @admin.display(description="Головне фото")
    def primary_preview(self, obj):
        if not obj.pk:
            return "Збережіть товар, потім додайте зображення нижче."
        return self.thumb(obj)


@admin.register(ProductVariant)
class ProductVariantAdmin(DropRoomModelAdmin):
    list_display = [
        "product",
        "size",
        "sku",
        "price",
        "stock_qty",
        "stock_status_label",
        "is_available",
    ]
    list_filter = [
        LowStockFilter,
        ("color", RelatedDropdownFilter),
    ]
    list_editable = ["stock_qty", "is_available"]
    search_fields = ["sku", "product__name"]
    autocomplete_fields = ["product", "color"]
    list_per_page = 40

    @admin.display(description="Статус")
    def stock_status_label(self, obj):
        if not obj.is_available:
            return format_html(
                '<span style="font-family:monospace;color:#888;">— Недоступний</span>'
            )
        if obj.stock_qty == 0:
            return format_html(
                '<span style="font-family:monospace;font-weight:700;color:#5b7fd4;">↻ Під замовлення</span>'
            )
        if obj.stock_qty <= 5:
            return format_html(
                '<span style="font-family:monospace;font-weight:700;color:#c45a14;">⚠ Мало</span>'
            )
        return format_html(
            '<span style="font-family:monospace;font-weight:700;color:#1c8551;">✓ В наявності</span>'
        )
