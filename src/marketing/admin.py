from django.contrib import admin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from config.admin_utils import DropRoomModelAdmin

from .models import DropNotification, NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(DropRoomModelAdmin):
    list_display = ["email", "is_active", "created_at"]
    list_filter = [("is_active", ChoicesDropdownFilter)]
    search_fields = ["email"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(DropNotification)
class DropNotificationAdmin(DropRoomModelAdmin):
    list_display = ["email", "drop", "user", "created_at"]
    list_filter = [
        ("drop", RelatedDropdownFilter),
    ]
    search_fields = ["email", "user__username"]
    autocomplete_fields = ["user", "drop"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
