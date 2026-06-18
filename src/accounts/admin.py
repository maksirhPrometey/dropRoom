from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from config.admin_utils import DropRoomModelAdmin

from .models import Address, UserProfile, WishlistItem

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ["username", "email", "first_name", "last_name", "is_staff", "date_joined"]
    list_filter = [("is_staff", ChoicesDropdownFilter), ("is_active", ChoicesDropdownFilter)]


@admin.register(UserProfile)
class UserProfileAdmin(DropRoomModelAdmin):
    list_display = ["user", "phone", "city", "newsletter_opt_in", "created_at"]
    list_filter = [("newsletter_opt_in", ChoicesDropdownFilter)]
    search_fields = ["user__username", "user__email", "phone", "city"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at"]


@admin.register(Address)
class AddressAdmin(DropRoomModelAdmin):
    list_display = [
        "user",
        "label",
        "city",
        "street",
        "building",
        "is_default",
    ]
    list_filter = [
        ("city", ChoicesDropdownFilter),
        ("is_default", ChoicesDropdownFilter),
    ]
    search_fields = ["user__username", "full_name", "city", "street"]
    autocomplete_fields = ["user"]
    fieldsets = [
        ("Клієнт", {"fields": ["user", "label", "is_default"]}),
        (
            "Отримувач",
            {"fields": ["full_name", "phone"]},
        ),
        (
            "Адреса",
            {
                "fields": [
                    "city",
                    "street",
                    "building",
                    "flat",
                    "np_warehouse",
                ],
            },
        ),
    ]


@admin.register(WishlistItem)
class WishlistItemAdmin(DropRoomModelAdmin):
    list_display = ["user", "variant", "added_at"]
    search_fields = ["user__username", "variant__sku", "variant__product__name"]
    autocomplete_fields = ["user", "variant"]
    readonly_fields = ["added_at"]
