"""Очищення taxonomy після помилкового імпорту Telegram."""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from src.catalog.models import Brand, Category, Product
from src.orders.models import CartItem, OrderItem
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.parser import _match_category, resolve_brand


def _bogus_brand_categories() -> list[Category]:
    """Category, чиї name/slug збігаються з Brand (Sandro тощо)."""
    brand_slugs = {
        s.lower()
        for s in Brand.objects.filter(is_active=True).values_list("slug", flat=True)
        if s
    }
    brand_names = {
        n.lower()
        for n in Brand.objects.filter(is_active=True).values_list("name", flat=True)
        if n
    }
    bogus: list[Category] = []
    for category in Category.objects.all():
        slug = (category.slug or "").lower()
        name = (category.name or "").lower()
        if slug in brand_slugs or name in brand_names:
            bogus.append(category)
    return bogus


def _best_caption(product: Product) -> str:
    captions = list(
        TelegramImport.objects.filter(product=product)
        .exclude(raw_caption="")
        .values_list("raw_caption", flat=True)
    )
    if not captions:
        return product.name or ""
    return max(captions, key=len)


def _fallback_category() -> Category | None:
    for slug in ("bags", "accessories", "sneakers"):
        category = Category.objects.filter(slug=slug).first()
        if category:
            return category
    return (
        Category.objects.exclude(slug__in=_bogus_slugs())
        .order_by("sort_order", "id")
        .first()
    )


def _bogus_slugs() -> set[str]:
    return {(c.slug or "").lower() for c in _bogus_brand_categories()}


def _is_junk_stub_product(product: Product) -> bool:
    """
    Службові репліки продавця в Telegram-групі («термін орієнтовний 14
    днів», «1 в наявності») імпортер іноді перетворював на «товар» —
    завжди рівно один варіант ONE SIZE за дефолтною TELEGRAM_DEFAULT_PRICE
    (бо в тексті взагалі не було ціни). Реальний товар без бренду
    («Стильний нейлоновий рюкзак…») завжди має свою фактичну ціну з
    caption, тож цей маркер не плутає їх.
    """
    variants = list(product.variants.all())
    if len(variants) != 1:
        return False
    variant = variants[0]
    if variant.size != "ONE SIZE":
        return False
    if variant.price != Decimal(settings.TELEGRAM_DEFAULT_PRICE):
        return False
    # Ніколи не чіпати товар, який хтось реально замовив чи додав у кошик.
    if OrderItem.objects.filter(variant=variant).exists():
        return False
    if CartItem.objects.filter(variant=variant).exists():
        return False
    return True


class Command(BaseCommand):
    help = (
        "1) Перепризначити товари з Category=імʼя бренду (Sandro…) на реальну "
        "категорію з caption.\n"
        "2) Видалити порожні bogus-категорії.\n"
        "3) Опційно: зняти is_active з товарів на Crocs без бренду в caption."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати план",
        )
        parser.add_argument(
            "--deactivate-no-brand",
            action="store_true",
            help=(
                "Деактивувати лише junk на crocs/першому бренді: "
                "«Товар з Telegram», Sold out у назві тощо"
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        deactivate = options["deactivate_no_brand"]
        fallback = _fallback_category()
        if not fallback:
            self.stderr.write(self.style.ERROR("Немає жодної легітимної Category"))
            return

        bogus = _bogus_brand_categories()
        self.stdout.write(
            f"Bogus categories: {[(c.pk, c.name, c.slug) for c in bogus]}"
        )

        moved = 0
        for category in bogus:
            products = Product.objects.filter(category=category).select_related(
                "brand", "category"
            )
            for product in products.iterator():
                caption = _best_caption(product)
                new_category = _match_category(caption) or fallback
                if new_category.pk == product.category_id:
                    continue
                moved += 1
                preview = (
                    f"product {product.pk} {product.name[:50]!r}: "
                    f"{product.category.slug} → {new_category.slug}"
                )
                if dry_run:
                    self.stdout.write(preview)
                    continue
                with transaction.atomic():
                    product.category = new_category
                    product.save(update_fields=["category"])
                self.stdout.write(self.style.SUCCESS(preview))

        deleted = 0
        for category in bogus:
            remaining = Product.objects.filter(category=category).count()
            if remaining:
                self.stderr.write(
                    self.style.WARNING(
                        f"Не видалено Category {category.pk} {category.name}: "
                        f"ще {remaining} товарів"
                    )
                )
                continue
            preview = f"delete Category {category.pk} {category.name!r} ({category.slug})"
            if dry_run:
                self.stdout.write(preview)
                deleted += 1
                continue
            category.delete()
            deleted += 1
            self.stdout.write(self.style.SUCCESS(preview))

        deactivated = 0
        if deactivate:
            crocs = Brand.objects.filter(slug="crocs").first()
            first = Brand.objects.filter(is_active=True).order_by("id").first()
            suspect_ids = {b.pk for b in (crocs, first) if b}
            qs = Product.objects.filter(
                brand_id__in=suspect_ids, is_active=True
            ).select_related("brand").prefetch_related("variants")
            for product in qs:
                if not _is_junk_stub_product(product):
                    continue
                caption = _best_caption(product)
                # Не чіпати, якщо caption/назва вже резолвиться в бренд
                if resolve_brand(caption) is not None:
                    continue
                if resolve_brand(product.name or "") is not None:
                    continue
                deactivated += 1
                preview = (
                    f"deactivate product {product.pk} "
                    f"{product.name[:50]!r} (brand={product.brand.name})"
                )
                if dry_run:
                    self.stdout.write(preview)
                    continue
                product.is_active = False
                product.save(update_fields=["is_active"])
                self.stdout.write(self.style.WARNING(preview))

        # статистика
        counts = (
            Category.objects.annotate(n=Count("products"))
            .filter(n__gt=0)
            .values_list("slug", "n")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{' (dry-run)' if dry_run else ''}: "
                f"переміщено {moved}, видалено category {deleted}, "
                f"деактивовано {deactivated}. Залишок: {list(counts)}"
            )
        )
