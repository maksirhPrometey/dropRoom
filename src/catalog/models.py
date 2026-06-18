from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    country = models.CharField(max_length=80, blank=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Бренд"
        verbose_name_plural = "Бренди"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("catalog:list") + f"?brand={self.slug}"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    LAYOUT_NORMAL = "normal"
    LAYOUT_WIDE = "wide"
    LAYOUT_BIG = "big"
    LAYOUT_CHOICES = [
        (LAYOUT_NORMAL, "Звичайна"),
        (LAYOUT_WIDE, "Широка (2 колонки)"),
        (LAYOUT_BIG, "Велика (3 колонки)"),
    ]
    VARIANT_LIGHT = "light"
    VARIANT_DARK = "dark"
    VARIANT_CHOICES = [
        (VARIANT_LIGHT, "Світла"),
        (VARIANT_DARK, "Темна (білий текст)"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    image = models.ImageField(
        upload_to="categories/",
        null=True,
        blank=True,
        help_text="Фото для плитки на головній і в каталозі.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    show_on_home = models.BooleanField(
        default=False,
        help_text="Показувати в блоці «Категорії / сезону» на головній.",
    )
    home_layout = models.CharField(
        max_length=10,
        choices=LAYOUT_CHOICES,
        default=LAYOUT_NORMAL,
    )
    home_variant = models.CharField(
        max_length=10,
        choices=VARIANT_CHOICES,
        default=VARIANT_LIGHT,
    )
    home_tag = models.CharField(
        max_length=30,
        blank=True,
        help_text="Плашка зверху: Featured, New тощо.",
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("catalog:list") + f"?category={self.slug}"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Color(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    hex_code = models.CharField(max_length=7)

    class Meta:
        ordering = ["name"]
        verbose_name = "Колір"
        verbose_name_plural = "Кольори"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Drop(models.Model):
    SEASON_CHOICES = [("S/S", "S/S"), ("F/W", "F/W")]

    number = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=200)
    theme = models.CharField(max_length=200, blank=True)
    season = models.CharField(max_length=10, choices=SEASON_CHOICES)
    year = models.PositiveSmallIntegerField()
    scheduled_at = models.DateTimeField()
    is_live = models.BooleanField(default=False)
    cover_image = models.ImageField(upload_to="drops/", null=True, blank=True)

    class Meta:
        ordering = ["-number"]
        verbose_name = "Дроп"
        verbose_name_plural = "Дропи"

    def __str__(self) -> str:
        return f"Drop {self.number:03d} — {self.title}"

    @property
    def number_display(self) -> str:
        return f"{self.number:03d}"


class Product(models.Model):
    GENDER_CHOICES = [("W", "Жіночий"), ("M", "Чоловічий"), ("U", "Унісекс")]

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    drop = models.ForeignKey(
        Drop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    material = models.CharField(max_length=255, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Стара ціна (до знижки)",
        help_text="Вкажіть якщо товар зі знижкою. Відображається перекресленою поруч з актуальною ціною.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Товар"
        verbose_name_plural = "Товари"

    def __str__(self) -> str:
        return f"{self.brand.name} — {self.name}"

    def get_absolute_url(self) -> str:
        return reverse("catalog:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(f"{self.brand.name}-{self.name}")
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def in_stock(self) -> bool:
        return self.variants.filter(is_available=True, stock_qty__gt=0).exists()

    @property
    def is_low_stock(self) -> bool:
        """True коли є в наявності, але у всіх доступних варіантах залишилось ≤5 шт."""
        in_stock = [v for v in self.variants.all() if v.is_available and v.stock_qty > 0]
        return bool(in_stock) and all(v.stock_qty <= 5 for v in in_stock)

    @property
    def is_under_order(self) -> bool:
        """True коли жоден варіант не має залишку, але хоча б один доступний для замовлення."""
        all_variants = list(self.variants.all())
        has_available = any(v.is_available for v in all_variants)
        has_stock = any(v.is_available and v.stock_qty > 0 for v in all_variants)
        return has_available and not has_stock

    @property
    def price(self):
        return self.base_price

    @property
    def discount_pct(self) -> int | None:
        """Відсоток знижки відносно старої ціни (ціле число, напр. 25)."""
        if self.compare_price and self.compare_price > self.base_price:
            return round((1 - self.base_price / self.compare_price) * 100)
        return None

    @property
    def badge_new(self) -> bool:
        from django.utils import timezone
        from datetime import timedelta
        return (timezone.now() - self.created_at).days <= 14

    @property
    def badge_drop(self) -> bool:
        return self.drop_id is not None

    @property
    def available_variants_preview(self):
        return self.variants.filter(is_available=True).order_by("size")[:6]

    @property
    def in_wishlist(self) -> bool:
        return getattr(self, "_in_wishlist", False)


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variants",
    )
    size = models.CharField(max_length=20)
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["size"]
        verbose_name = "Варіант"
        verbose_name_plural = "Варіанти"

    def __str__(self) -> str:
        return f"{self.product.name} / {self.size}"

    LOW_STOCK_THRESHOLD = 5

    @property
    def in_stock(self) -> bool:
        return self.stock_qty > 0 and self.is_available

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock_qty <= self.LOW_STOCK_THRESHOLD and self.is_available

    @property
    def size_display(self) -> str:
        return self.size

    @property
    def size_label(self) -> str:
        if self.in_stock:
            return self.size
        return f"{self.size} - Під замовлення"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Зображення"
        verbose_name_plural = "Зображення"

    def __str__(self) -> str:
        return f"{self.product.name} #{self.sort_order}"
