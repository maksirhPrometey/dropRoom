from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    free_delivery_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=3000
    )
    return_period_days = models.PositiveSmallIntegerField(default=14)
    pickup_reserve_hours = models.PositiveSmallIntegerField(default=24)
    support_hours = models.CharField(
        max_length=100, default="09:00 — 23:00, щодня"
    )
    response_time_mins = models.PositiveSmallIntegerField(default=4)
    telegram_support = models.CharField(max_length=50, default="@droproom_support")
    telegram_channel = models.CharField(max_length=50, default="@droproom_drops")
    phone_main = models.CharField(max_length=20, blank=True)
    email_main = models.EmailField(default="hello@droproom.ua")
    email_press = models.EmailField(default="press@droproom.ua")
    instagram_url = models.URLField(blank=True)
    founded_year = models.PositiveSmallIntegerField(default=2019)
    footer_desc = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Налаштування сайту"
        verbose_name_plural = "Налаштування сайту"

    def __str__(self) -> str:
        return "Налаштування сайту"


class UtilityBarItem(models.Model):
    text = models.CharField(max_length=200)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Рядок анонсу"
        verbose_name_plural = "Рядки анонсів"

    def __str__(self) -> str:
        return self.text


class HomePage(SingletonModel):
    hero_blurb = models.TextField(blank=True)
    hero_slider_autoplay_enabled = models.BooleanField(
        default=True,
        verbose_name="Автопрокрут",
        help_text="Увімкнути автоматичне гортання слайдів.",
    )
    hero_slider_autoplay_seconds = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Інтервал автопрокруту (сек)",
        help_text="Затримка між слайдами, від 2 до 60 секунд.",
        validators=[MinValueValidator(2), MaxValueValidator(60)],
    )
    editorial_stamp = models.CharField(max_length=100, blank=True)
    editorial_image = models.ImageField(
        upload_to="pages/home/", null=True, blank=True
    )
    editorial_eyebrow = models.CharField(max_length=100, blank=True)
    editorial_title_main = models.CharField(max_length=100, blank=True)
    editorial_title_accent = models.CharField(max_length=100, blank=True)
    editorial_body_1 = models.TextField(blank=True)
    editorial_body_2 = models.TextField(blank=True)
    newsletter_heading_1 = models.CharField(max_length=100, blank=True)
    newsletter_heading_2 = models.CharField(max_length=100, blank=True)
    newsletter_heading_3 = models.CharField(max_length=100, blank=True)
    newsletter_subtext = models.TextField(blank=True)
    newsletter_counter_label = models.CharField(max_length=60, blank=True)

    class Meta:
        verbose_name = "Головна сторінка"
        verbose_name_plural = "Головна сторінка"

    def __str__(self) -> str:
        return "Головна сторінка"


class HeroSlideImage(models.Model):
    page = models.ForeignKey(
        HomePage,
        on_delete=models.CASCADE,
        related_name="hero_slides",
    )
    image = models.ImageField(
        upload_to="pages/home/hero/",
        verbose_name="Фото",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Порядок",
        help_text="0 = автоматично в кінець списку.",
    )
    eyebrow = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Плашка зверху",
        help_text="Напр.: OUTLET — ОРИГІНАЛЬНІ БРЕНДИ",
    )
    title_line1 = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Заголовок (частина 1)",
        help_text="Напр.: СТИЛЬ,",
    )
    title_accent = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Заголовок (акцент)",
        help_text="Напр.: ЩО В ТЕБЕ. — виділяється кольором.",
    )
    subtitle = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Підзаголовок",
    )
    usp_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Рамка USP",
        help_text="Напр.: ДОСТУПНО. ВИГІДНО. ОРИГІНАЛЬНО.",
    )
    feature_1 = models.CharField(max_length=80, blank=True, verbose_name="Перевага 1")
    feature_2 = models.CharField(max_length=80, blank=True, verbose_name="Перевага 2")
    feature_3 = models.CharField(max_length=80, blank=True, verbose_name="Перевага 3")
    cta_text = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Текст кнопки",
        help_text="Напр.: Перейти до аутлету",
    )
    link = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Посилання кнопки",
        help_text="URL або шлях (/catalog/). Порожнє — каталог.",
    )

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "Слайд hero"
        verbose_name_plural = "Слайди hero"

    def __str__(self) -> str:
        label = self.title_line1 or self.eyebrow or f"Слайд {self.sort_order or self.pk}"
        return label


class HeroPromoItem(models.Model):
    ICON_TAG = "tag"
    ICON_PERCENT = "percent"
    ICON_CLOCK = "clock"
    ICON_CHOICES = [
        (ICON_TAG, "Цінник"),
        (ICON_PERCENT, "Знижка"),
        (ICON_CLOCK, "Ліміт"),
    ]

    page = models.ForeignKey(
        HomePage,
        on_delete=models.CASCADE,
        related_name="hero_promos",
    )
    icon = models.CharField(
        max_length=20,
        choices=ICON_CHOICES,
        default=ICON_TAG,
        verbose_name="Іконка",
    )
    title = models.CharField(max_length=80, verbose_name="Заголовок")
    description = models.CharField(max_length=200, verbose_name="Опис")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "Промо під hero"
        verbose_name_plural = "Промо під hero"

    def __str__(self) -> str:
        return self.title


class StatBlock(models.Model):
    page = models.ForeignKey(
        HomePage, on_delete=models.CASCADE, related_name="stat_blocks"
    )
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Блок статистики"
        verbose_name_plural = "Блоки статистики"

    def __str__(self) -> str:
        return f"{self.value} — {self.label}"


class CatalogPage(SingletonModel):
    hero_title_main = models.CharField(max_length=200, default="Всі бренди /")
    hero_title_accent = models.CharField(max_length=200, default="всі дропи")
    hero_blurb = models.TextField(blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Сторінка каталогу"
        verbose_name_plural = "Сторінка каталогу"

    def __str__(self) -> str:
        return "Сторінка каталогу"


class StoryPage(SingletonModel):
    hero_title_1 = models.CharField(max_length=100, blank=True)
    hero_title_2 = models.CharField(max_length=100, blank=True)
    hero_title_accent = models.CharField(max_length=100, blank=True)
    hero_lead = models.TextField(blank=True)
    pillars_heading = models.CharField(max_length=200, blank=True)
    timeline_heading_main = models.CharField(max_length=100, blank=True)
    timeline_heading_2 = models.CharField(max_length=100, blank=True)
    timeline_heading_accent = models.CharField(max_length=100, blank=True)
    timeline_intro = models.TextField(blank=True)
    quote_text = models.TextField(blank=True)
    quote_author = models.CharField(max_length=200, blank=True)
    cta_heading_1 = models.CharField(max_length=100, blank=True)
    cta_heading_2 = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Сторінка про нас"
        verbose_name_plural = "Сторінка про нас"

    def __str__(self) -> str:
        return "Сторінка про нас"


class StoryPillar(models.Model):
    page = models.ForeignKey(
        StoryPage, on_delete=models.CASCADE, related_name="pillars"
    )
    number = models.PositiveSmallIntegerField()
    title_line1 = models.CharField(max_length=100)
    title_line2 = models.CharField(max_length=100)
    body = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Принцип"
        verbose_name_plural = "Принципи"

    def __str__(self) -> str:
        return f"{self.title_line1} {self.title_line2}"


class StoryTimelineEvent(models.Model):
    page = models.ForeignKey(
        StoryPage, on_delete=models.CASCADE, related_name="timeline_events"
    )
    year = models.CharField(max_length=10)
    is_accent_year = models.BooleanField(default=False)
    heading = models.CharField(max_length=200)
    body = models.TextField()
    drop_tag = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Подія хронології"
        verbose_name_plural = "Хронологія"

    def __str__(self) -> str:
        return f"{self.year} — {self.heading}"


class TeamMember(models.Model):
    page = models.ForeignKey(
        StoryPage, on_delete=models.CASCADE, related_name="team_members"
    )
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="pages/team/", null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Член команди"
        verbose_name_plural = "Команда"

    def __str__(self) -> str:
        return self.name


class ContactsPage(SingletonModel):
    hero_lead = models.TextField(blank=True)
    channels_desc = models.TextField(blank=True)
    form_heading_1 = models.CharField(max_length=100, blank=True)
    form_heading_2 = models.CharField(max_length=100, blank=True)
    form_heading_accent = models.CharField(max_length=100, blank=True)
    form_aside_body = models.TextField(blank=True)
    faq_heading_main = models.CharField(max_length=100, blank=True)
    faq_heading_accent = models.CharField(max_length=100, blank=True)
    faq_intro = models.TextField(blank=True)

    class Meta:
        verbose_name = "Сторінка контактів"
        verbose_name_plural = "Сторінка контактів"

    def __str__(self) -> str:
        return "Сторінка контактів"


class Store(models.Model):
    page = models.ForeignKey(
        ContactsPage, on_delete=models.CASCADE, related_name="stores"
    )
    city = models.CharField(max_length=100)
    label = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255)
    hours = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    telegram = models.CharField(max_length=50, blank=True)
    pickup_eta = models.CharField(max_length=50, blank=True)
    maps_url = models.URLField(null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Магазин"
        verbose_name_plural = "Магазини"

    def __str__(self) -> str:
        return f"{self.city} — {self.address}"


class ContactChannel(models.Model):
    page = models.ForeignKey(
        ContactsPage, on_delete=models.CASCADE, related_name="channels"
    )
    label = models.CharField(max_length=50)
    value = models.CharField(max_length=100)
    meta = models.CharField(max_length=200, blank=True)
    url = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Канал зв'язку"
        verbose_name_plural = "Канали зв'язку"

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"


class FAQItem(models.Model):
    page = models.ForeignKey(
        ContactsPage, on_delete=models.CASCADE, related_name="faq_items"
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"

    def __str__(self) -> str:
        return self.question
