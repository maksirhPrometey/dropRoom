from django.contrib import admin
from django.db.models import Max
from django.utils.html import format_html
from unfold.admin import StackedInline, TabularInline

from config.admin_utils import DropRoomModelAdmin, SingletonAdminMixin, image_preview

from .models import (
    CatalogPage,
    ContactChannel,
    ContactsPage,
    FAQItem,
    HeroPromoItem,
    HeroSlideImage,
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


class HeroSlideImageInline(StackedInline):
    model = HeroSlideImage
    extra = 1
    min_num = 0
    readonly_fields = ["image_preview"]
    ordering = ["sort_order"]
    verbose_name = "Слайд"
    verbose_name_plural = "Слайди hero"
    classes = ["hero-slide-inline"]
    fieldsets = [
        (
            None,
            {"fields": ["sort_order", "image", "image_preview"]},
        ),
        (
            "Текст на слайді",
            {
                "fields": [
                    "eyebrow",
                    "title_line1",
                    "title_accent",
                    "subtitle",
                    "usp_text",
                ],
            },
        ),
        (
            "Переваги",
            {"fields": ["feature_1", "feature_2", "feature_3"]},
        ),
        (
            "Кнопка",
            {"fields": ["cta_text", "link"]},
        ),
    ]

    @admin.display(description="Превʼю")
    def image_preview(self, obj: HeroSlideImage) -> str:
        if obj and obj.image:
            return format_html(
                '<img src="{}" alt="" width="320" height="auto" '
                'style="object-fit:cover;border-radius:4px;border:1px solid #d6d2c8;" />',
                obj.image.url,
            )
        return "—"


class HeroPromoItemInline(TabularInline):
    model = HeroPromoItem
    extra = 0
    max_num = 3
    fields = ["sort_order", "icon", "title", "description"]
    ordering = ["sort_order"]
    verbose_name = "Промо"
    verbose_name_plural = "Промо під hero (3 колонки)"


class StatBlockInline(TabularInline):
    model = StatBlock
    extra = 0
    fields = ["label", "value", "description", "sort_order"]
    ordering = ["sort_order"]
    classes = ["collapse"]
    verbose_name_plural = "Блоки статистики"


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
    inlines = [HeroSlideImageInline, HeroPromoItemInline, StatBlockInline]
    readonly_fields = ["editorial_preview"]
    fieldsets = [
        (
            "Hero-слайдер",
            {
                "fields": [
                    "hero_slider_autoplay_enabled",
                    "hero_slider_autoplay_seconds",
                ],
                "description": (
                    "Додайте слайди з фото та текстом (як на макеті). "
                    "Менший «Порядок» = слайд показується раніше. "
                    "Під hero — до 3 промо-колонок."
                ),
            },
        ),
        (
            "Головний екран",
            {"fields": ["hero_blurb"], "classes": ["collapse"]},
        ),
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
                "classes": ["collapse"],
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
                "classes": ["collapse"],
            },
        ),
    ]

    editorial_preview = image_preview("editorial_image", width=280, height=160)

    def save_formset(self, request, form, formset, change) -> None:
        instances = formset.save(commit=False)
        home = form.instance

        for obj in instances:
            if isinstance(obj, HeroSlideImage):
                obj.page = home
                if obj.sort_order == 0:
                    current_max = (
                        HeroSlideImage.objects.filter(page=home)
                        .exclude(pk=obj.pk)
                        .aggregate(m=Max("sort_order"))
                        .get("m")
                        or 0
                    )
                    obj.sort_order = current_max + 1
            obj.save()

        for obj in formset.deleted_objects:
            obj.delete()

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        home = HomePage.load()
        extra_context["subtitle"] = (
            f"Фото в слайдері: {home.hero_slides.count()}"
        )
        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
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
