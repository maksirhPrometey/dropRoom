from django.contrib import admin
from django.db.models import Q
from django.urls import reverse
from django.utils.html import format_html
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


@admin.register(HeroStripCard)
class HeroStripCardAdmin(DropRoomModelAdmin):
    list_display = [
        "thumb",
        "label",
        "cta_text",
        "link_short",
        "sort_order",
        "is_active",
    ]
    list_display_links = ["label"]
    list_editable = ["sort_order", "is_active"]
    list_filter = ["is_active"]
    ordering = ["sort_order", "pk"]
    search_fields = ["label", "cta_text", "link"]
    readonly_fields = ["image_preview_large"]
    exclude = ["page"]

    fieldsets = [
        (
            "Показ на сайті",
            {
                "fields": ["is_active", "sort_order"],
                "description": "Менший «Порядок» — слайд показується раніше.",
            },
        ),
        (
            "Фото",
            {
                "fields": ["image", "image_preview_large"],
                "description": "Рекомендований розмір: 1800×760 px або ширше, landscape.",
            },
        ),
        (
            "Підписи та посилання",
            {
                "fields": ["label", "cta_text", "link"],
                "description": (
                    "«Підпис» — зліва на слайді. «Текст кнопки» — справа. "
                    "Посилання порожнє → відкриється каталог."
                ),
            },
        ),
    ]

    thumb = image_preview("image", width=120, height=68)
    image_preview_large = image_preview("image", width=480, height=220)

    @admin.display(description="Посилання")
    def link_short(self, obj: HeroStripCard) -> str:
        if not obj.link:
            return "→ Каталог"
        if len(obj.link) > 40:
            return f"{obj.link[:37]}..."
        return obj.link

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(page_id=1)

    def save_model(self, request, obj, form, change) -> None:
        obj.page = HomePage.load()
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        home = HomePage.load()
        slides = HeroStripCard.objects.filter(page=home)
        extra_context["title"] = "Hero-слайдер — фото на головній"
        extra_context["subtitle"] = (
            f"Активних слайдів з фото: "
            f"{slides.filter(is_active=True).exclude(Q(image='') | Q(image__isnull=True)).count()} "
            f"· усього: {slides.count()}"
        )
        return super().changelist_view(request, extra_context=extra_context)


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
    inlines = [StatBlockInline]
    readonly_fields = ["editorial_preview", "hero_slides_manage"]
    fieldsets = [
        (
            "Hero-слайдер",
            {
                "fields": [
                    "hero_slider_autoplay_enabled",
                    "hero_slider_autoplay_seconds",
                    "hero_slides_manage",
                ],
                "description": (
                    "Тут — лише автопрокрут. Фото, підписи та кнопки "
                    "редагуються в розділі «Hero-слайдер» у меню зліва."
                ),
            },
        ),
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

    @admin.display(description="Слайди")
    def hero_slides_manage(self, obj: HomePage) -> str:
        slides = HeroStripCard.objects.filter(page=obj)
        active_count = slides.filter(is_active=True).exclude(
            Q(image="") | Q(image__isnull=True)
        ).count()
        slides_url = reverse("admin:pages_herostripcard_changelist")
        add_url = reverse("admin:pages_herostripcard_add")
        return format_html(
            '<p style="margin:0 0 10px;line-height:1.5;">'
            "На сайті зараз: <strong>{}</strong> активних слайдів з фото "
            "(усього в базі: {}). Без фото слайд не показується."
            "</p>"
            '<p style="margin:0;display:flex;flex-wrap:wrap;gap:8px;">'
            '<a href="{}" class="button">Усі слайди</a>'
            '<a href="{}" class="button">+ Додати слайд</a>'
            "</p>",
            active_count,
            slides.count(),
            slides_url,
            add_url,
        )


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
