"""Спільні утиліти для django-unfold адмінки DropRoom."""

from django.contrib.admin import display
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin


class SingletonAdminMixin:
    """Редірект зі списку одразу на єдиний запис (pk=1)."""

    def has_add_permission(self, request) -> bool:
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = self.model.objects.get_or_create(pk=1)
        url_name = (
            f"admin:{self.model._meta.app_label}_"
            f"{self.model._meta.model_name}_change"
        )
        return HttpResponseRedirect(reverse(url_name, args=[obj.pk]))


def image_preview(field_name: str, *, width: int = 80, height: int = 80):
    """Фабрика readonly-методу для превʼю ImageField."""

    @display(description="Превʼю")
    def _preview(self, obj):
        image = getattr(obj, field_name, None)
        if not image:
            return "—"
        return format_html(
            '<img src="{}" alt="" width="{}" height="{}" '
            'style="object-fit:cover;border-radius:4px;border:1px solid #d6d2c8;" />',
            image.url,
            width,
            height,
        )

    return _preview


def color_swatch_display(hex_attr: str = "hex_code"):
    @display(description="Колір")
    def _swatch(self, obj):
        hex_value = getattr(obj, hex_attr, "") or "#cccccc"
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:8px;">'
            '<span style="width:22px;height:22px;border-radius:50%;'
            "background:{};border:1px solid rgba(0,0,0,.15);\"></span>"
            "<code>{}</code></span>",
            hex_value,
            hex_value,
        )

    return _swatch


class DropRoomModelAdmin(ModelAdmin):
    """Базовий ModelAdmin з компактним списком і зручними фільтрами."""

    list_per_page = 25
    show_full_result_count = False
