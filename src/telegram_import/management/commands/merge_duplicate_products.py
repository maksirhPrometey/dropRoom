"""
Об'єднати товари-дублікати, які виникли через повторні/відредаговані
пости в Telegram із НЕ ідентичним (на відміну від `dedupe_telegram_products`,
який дедублікує лише 1:1 однаковий raw_caption) текстом підпису — той самий
товар («Moon Boot», «Coach Shoulder Bag») опублікований кілька разів і
Product.save() лише додав «-1», «-2» до slug, замість оновлення існуючого.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from src.catalog.models import Product
from src.orders.models import CartItem, OrderItem
from src.telegram_import.models import TelegramImport


def _has_real_orders(product: Product) -> bool:
    variant_ids = list(product.variants.values_list("pk", flat=True))
    if not variant_ids:
        return False
    if OrderItem.objects.filter(variant_id__in=variant_ids).exists():
        return True
    if CartItem.objects.filter(variant_id__in=variant_ids).exists():
        return True
    return False


def _pick_survivor(products: list[Product]) -> Product:
    def rank(product: Product) -> tuple[int, int, int]:
        return (
            product.variants.count(),
            product.images.count(),
            product.pk,
        )

    return max(products, key=rank)


class Command(BaseCommand):
    help = (
        "Знайти товари з однаковим брендом+назвою, але різним slug "
        "(«moon-boot», «moon-boot-1», «moon-boot-2») — залишок повторних "
        "постів у Telegram. Об'єднує лише групи з ОДНАКОВОЮ base_price "
        "у всіх дублікатах (сильний сигнал, що це той самий допис); "
        "групи з різною ціною лише виводяться для ручної перевірки."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати план без змін у БД",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        groups: dict[tuple[int | None, str], list[Product]] = defaultdict(list)
        qs = Product.objects.filter(is_active=True).select_related("brand").prefetch_related(
            "variants", "images"
        )
        for product in qs:
            key = (product.brand_id, (product.name or "").strip().lower())
            groups[key].append(product)

        merged_groups = 0
        removed_total = 0
        needs_review: list[str] = []

        for (_brand_id, _name), products in groups.items():
            if len(products) < 2:
                continue

            prices = {p.base_price for p in products}
            if len(prices) > 1:
                needs_review.append(
                    f"{products[0].brand.name} — {products[0].name!r}: "
                    f"PK {[p.pk for p in products]}, ціни {sorted(prices)} — "
                    f"РІЗНІ, потрібна ручна перевірка"
                )
                continue

            if any(_has_real_orders(p) for p in products):
                needs_review.append(
                    f"{products[0].brand.name} — {products[0].name!r}: "
                    f"PK {[p.pk for p in products]} — у когось із дублікатів "
                    f"є замовлення/кошик, не чіпаю автоматично"
                )
                continue

            survivor = _pick_survivor(products)
            duplicates = [p for p in products if p.pk != survivor.pk]

            preview = (
                f"{survivor.brand.name} — {survivor.name!r}: "
                f"лишаю #{survivor.pk} (slug={survivor.slug}), "
                f"видаляю {[p.pk for p in duplicates]}"
            )

            if dry_run:
                self.stdout.write(preview)
                merged_groups += 1
                removed_total += len(duplicates)
                continue

            with transaction.atomic():
                TelegramImport.objects.filter(
                    product_id__in=[p.pk for p in duplicates]
                ).update(product=survivor)
                for dup in duplicates:
                    dup.delete()

            merged_groups += 1
            removed_total += len(duplicates)
            self.stdout.write(self.style.SUCCESS(preview))

        if needs_review:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Потребують ручної перевірки:"))
            for line in needs_review:
                self.stdout.write(f"  {line}")

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: об'єднано груп {merged_groups}, "
                f"видалено товарів {removed_total}, "
                f"потребують ручної перевірки {len(needs_review)}"
            )
        )
