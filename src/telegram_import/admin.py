from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from config.admin_utils import DropRoomModelAdmin

from .models import TelegramImport, TelegramSyncState


@admin.register(TelegramImport)
class TelegramImportAdmin(DropRoomModelAdmin):
    list_display = [
        "message_id",
        "channel_id",
        "status",
        "product_link",
        "media_group_id",
        "created_at",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("product", RelatedDropdownFilter),
    ]
    search_fields = ["message_id", "raw_caption", "media_group_id", "error"]
    readonly_fields = [
        "channel_id",
        "message_id",
        "media_group_id",
        "raw_caption",
        "photo_file_ids",
        "imported_at",
        "created_at",
        "updated_at",
        "product_link",
    ]
    autocomplete_fields = ["product"]
    ordering = ["-created_at"]

    @admin.display(description="Товар")
    def product_link(self, obj):
        if not obj.product_id:
            return "—"
        url = reverse("admin:catalog_product_change", args=[obj.product_id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)


@admin.register(TelegramSyncState)
class TelegramSyncStateAdmin(DropRoomModelAdmin):
    list_display = ["channel_id", "last_message_id", "last_sync_at"]
    readonly_fields = ["last_sync_at"]
    ordering = ["-last_sync_at"]
