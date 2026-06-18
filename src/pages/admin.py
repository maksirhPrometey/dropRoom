from django.contrib import admin
from unfold.admin import StackedInline, TabularInline

from config.admin_utils import DropRoomModelAdmin, SingletonAdminMixin, image_preview

from .models import (
    CatalogPage,
    ContactChannel,
    ContactsPage,
    FAQItem,
    HeroStripCard,
    HomePage,
    SiteSettings,
    StatBlock,
    Store,
    StoryPage,
    StoryPillar,
    StoryTimelineEvent,
    TeamMember,
    UtilityBarItem,
)


class HeroStripCardInline(StackedInline):
    model = HeroStripCard
    extra = 0
    ordering = ["sort_order"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "sort_order",
                    "layout",
                    "is_active",
                    "image",
                    "label",
                    "title",
                    "meta",
                    "link",
                ],
                "description": (
                    "Завантажте «image» — це фото на всю картку. "
                    "У заголовку можна перенос: Outerwear /<br>Spring Layers"
                ),
            },
        ),
        (
            "Тільки для типу «Дроп»",
            {
                "fields": ["use_live_drop", "drop_label"],
                "classes": ["collapse"],
            },
        ),
    ]


class StatBlockInline(TabularInline):
    model = StatBlock
    extra = 0
    fields = ["label", "value", "description", "sort_order"]
    ordering = ["sort_order"]


class StoryPillarInline(TabularInline):
    model = StoryPillar
    extra = 0
    fields = ["number", "title_line1", "title_line2", "body", "sort_order"]
    ordering = ["sort_order"]


class StoryTimelineEventInline(TabularInline):
    model = StoryTimelineEvent
    extra = 0
    fields = [
        "year",
        "is_accent_year",
        "heading",
        "body",
        "drop_tag",
        "sort_order",
    ]
    ordering = ["sort_order"]


class TeamMemberInline(TabularInline):
    model = TeamMember
    extra = 0
    fields = ["name", "role", "photo", "sort_order", "is_active"]
    ordering = ["sort_order"]


class StoreInline(TabularInline):
    model = Store
    extra = 0
    fields = [
        "city",
        "label",
        "address",
        "hours",
        "phone",
        "telegram",
        "pickup_eta",
        "sort_order",
        "is_active",
    ]
    ordering = ["sort_order"]


class ContactChannelInline(TabularInline):
    model = ContactChannel
    extra = 0
    fields = ["label", "value", "meta", "url", "sort_order", "is_active"]
    ordering = ["sort_order"]


class FAQItemInline(TabularInline):
    model = FAQItem
    extra = 0
    fields = ["question", "answer", "sort_order", "is_active"]
    ordering = ["sort_order"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdminMixin, DropRoomModelAdmin):
    fieldsets = [
        (
            "Доставка та підтримка",
            {
                "fields": [
                    "free_delivery_threshold",
                    "return_period_days",
                    "pickup_reserve_hours",
                    "support_hours",
                    "response_time_mins",
                ],
                "description": "Пороги та тексти для кошика, футера та банерів.",
            },
        ),
        (
            "Контакти",
            {
                "fields": [
                    "telegram_support",
                    "telegram_channel",
                    "phone_main",
                    "email_main",
                    "email_press",
                    "instagram_url",
                ],
            },
        ),
        (
            "Загальне",
            {"fields": ["founded_year", "footer_desc"]},
        ),
    ]


@admin.register(UtilityBarItem)
class UtilityBarItemAdmin(DropRoomModelAdmin):
    list_display = ["text", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    ordering = ["sort_order"]
    search_fields = ["text"]


@admin.register(HomePage)
class HomePageAdmin(SingletonAdminMixin, DropRoomModelAdmin):
    inlines = [HeroStripCardInline, StatBlockInline]
    readonly_fields = ["editorial_preview"]
    fieldsets = [
        ("Головний екран", {"fields": ["hero_blurb"]}),
        (
            "Editorial-блок",
            {
                "fields": [
                    "editorial_stamp",
                    "editorial_image",
                    "editorial_preview",
                    "editorial_eyebrow",
                    "editorial_title_main",
                    "editorial_title_accent",
                    "editorial_body_1",
                    "editorial_body_2",
                ],
            },
        ),
        (
            "Розсилка",
            {
                "fields": [
                    "newsletter_heading_1",
                    "newsletter_heading_2",
                    "newsletter_heading_3",
                    "newsletter_subtext",
                    "newsletter_counter_label",
                ],
            },
        ),
    ]

    editorial_preview = image_preview("editorial_image", width=280, height=160)


@admin.register(CatalogPage)
class CatalogPageAdmin(SingletonAdminMixin, DropRoomModelAdmin):
    fieldsets = [
        (
            "Hero каталогу",
            {"fields": ["hero_title_main", "hero_title_accent", "hero_blurb"]},
        ),
        ("SEO", {"fields": ["seo_title", "seo_description"], "classes": ["collapse"]}),
    ]


@admin.register(StoryPage)
class StoryPageAdmin(SingletonAdminMixin, DropRoomModelAdmin):
    inlines = [StoryPillarInline, StoryTimelineEventInline, TeamMemberInline]
    fieldsets = [
        (
            "Hero",
            {
                "fields": [
                    "hero_title_1",
                    "hero_title_2",
                    "hero_title_accent",
                    "hero_lead",
                ],
            },
        ),
        ("Принципи", {"fields": ["pillars_heading"]}),
        (
            "Хронологія",
            {
                "fields": [
                    "timeline_heading_main",
                    "timeline_heading_2",
                    "timeline_heading_accent",
                    "timeline_intro",
                ],
            },
        ),
        ("Цитата", {"fields": ["quote_text", "quote_author"]}),
        ("CTA", {"fields": ["cta_heading_1", "cta_heading_2"]}),
    ]


@admin.register(ContactsPage)
class ContactsPageAdmin(SingletonAdminMixin, DropRoomModelAdmin):
    inlines = [StoreInline, ContactChannelInline, FAQItemInline]
    fieldsets = [
        ("Hero", {"fields": ["hero_lead"]}),
        ("Канали зв'язку", {"fields": ["channels_desc"]}),
        (
            "Форма зворотного зв'язку",
            {
                "fields": [
                    "form_heading_1",
                    "form_heading_2",
                    "form_heading_accent",
                    "form_aside_body",
                ],
            },
        ),
        (
            "FAQ",
            {
                "fields": [
                    "faq_heading_main",
                    "faq_heading_accent",
                    "faq_intro",
                ],
            },
        ),
    ]
