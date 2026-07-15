"""Злити лінійку UGG Golden* в один товар з варіантами-моделями."""

from __future__ import annotations

import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.utils.text import slugify

from src.accounts.models import WishlistItem
from src.catalog.models import Category, Color, Product, ProductVariant
from src.orders.models import CartItem, OrderItem
from src.telegram_import.models import TelegramImport

# Порядок важливий: Slide перед GoldenGlow.
_MODEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"goldenstar\s*clog", re.I), "Goldenstar Clog"),
    (re.compile(r"goldenglow\s*slide", re.I), "GoldenGlow Slide"),
    (re.compile(r"goldenglow", re.I), "GoldenGlow"),
    (re.compile(r"goldenrise", re.I), "Goldenrise"),
]

_MODEL_HEX: dict[str, str] = {
    "Goldenstar Clog": "#c4a574",
    "GoldenGlow Slide": "#e8d5b0",
    "GoldenGlow": "#d4af37",
    "Goldenrise": "#f5e6c8",
}

TARGET_NAME = "UGG Golden"
TARGET_SLUG = "ugg-golden"


def _model_from_name(name: str) -> str | None:
    for pattern, model in _MODEL_PATTERNS:
        if pattern.search(name or ""):
            return model
    return None


def _get_or_create_model_color(model: str) -> Color:
    color, created = Color.objects.get_or_create(
        name=model[:80],
        defaults={
            "slug": slugify(model) or "model",
            "hex_code": _MODEL_HEX.get(model, "#cccccc"),
        },
    )
    if not created and color.hex_code == "#cccccc" and model in _MODEL_HEX:
        color.hex_code = _MODEL_HEX[model]
        color.save(update_fields=["hex_code"])
    return color


def _unique_sku(base: str, used: set[str]) -> str:
    candidate = base[:64]
    if candidate not in used:
        return candidate
    n = 1
    while True:
        suffix = f"-{n}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        if candidate not in used:
            return candidate
        n += 1


class Command(BaseCommand):
    help = (
        "Обʼєднати UGG Goldenrise / GoldenGlow / Goldenstar Clog / GoldenGlow Slide "
        "в один товар з варіантами кольору=модель."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Лише план")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        footwear = Category.objects.filter(slug="footwear").first()
        if not footwear:
            self.stderr.write("Немає category footwear")
            return

        qs = (
            Product.objects.filter(brand__slug="ugg")
            .filter(
                Q(name__icontains="goldenrise")
                | Q(name__icontains="goldenglow")
                | Q(name__icontains="goldenstar")
            )
            .annotate(
                vcount=Count("variants", distinct=True),
                icount=Count("images", distinct=True),
            )
            .order_by("-vcount", "-icount", "pk")
        )
        products = list(qs)
        if len(products) < 2:
            self.stdout.write(f"Знайдено {len(products)} товарів — merge не потрібен")
            return

        by_model: dict[str, list[Product]] = {}
        for product in products:
            model = _model_from_name(product.name)
            if not model:
                self.stdout.write(f"skip (не модель лінійки): {product.pk} {product.name}")
                continue
            by_model.setdefault(model, []).append(product)

        if not by_model:
            self.stdout.write("Немає товарів лінійки Golden*")
            return

        survivor = products[0]
        others = [p for p in products if p.pk != survivor.pk]

        self.stdout.write(
            f"survivor={survivor.pk} {survivor.name!r} "
            f"(variants={survivor.vcount}, images={survivor.icount})"
        )
        for model, group in sorted(by_model.items()):
            ids = [p.pk for p in group]
            self.stdout.write(f"  {model}: {ids}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"dry-run: → {TARGET_NAME!r} slug={TARGET_SLUG} "
                    f"cat=footwear, remove {len(others)} products"
                )
            )
            return

        with transaction.atomic():
            used_skus = set(ProductVariant.objects.values_list("sku", flat=True))

            # Спочатку позначити кольори на варіантах survivor за його моделлю
            survivor_model = _model_from_name(survivor.name) or "Goldenstar Clog"
            survivor_color = _get_or_create_model_color(survivor_model)
            for variant in survivor.variants.filter(color__isnull=True):
                variant.color = survivor_color
                variant.save(update_fields=["color"])

            for donor in others:
                model = _model_from_name(donor.name)
                if not model:
                    continue
                color = _get_or_create_model_color(model)

                for variant in list(donor.variants.all()):
                    existing = ProductVariant.objects.filter(
                        product=survivor,
                        color=color,
                        size=variant.size,
                    ).first()
                    if existing:
                        existing.stock_qty = max(existing.stock_qty, variant.stock_qty)
                        existing.is_available = existing.is_available or variant.is_available
                        if variant.price and (
                            not existing.price or variant.price < existing.price
                        ):
                            # лишаємо нижчу ненульову як card price для розміру
                            if variant.price > 0:
                                existing.price = variant.price
                        existing.save()
                        taken_users = set(
                            WishlistItem.objects.filter(variant=existing).values_list(
                                "user_id", flat=True
                            )
                        )
                        for item in WishlistItem.objects.filter(variant=variant):
                            if item.user_id in taken_users:
                                item.delete()
                            else:
                                item.variant = existing
                                item.save(update_fields=["variant"])
                                taken_users.add(item.user_id)
                        for cart_item in CartItem.objects.filter(variant=variant):
                            clash = CartItem.objects.filter(
                                cart_id=cart_item.cart_id, variant=existing
                            ).first()
                            if clash:
                                clash.quantity = max(clash.quantity, cart_item.quantity)
                                clash.save(update_fields=["quantity"])
                                cart_item.delete()
                            else:
                                cart_item.variant = existing
                                cart_item.save(update_fields=["variant"])
                        OrderItem.objects.filter(variant=variant).update(variant=existing)
                        variant.delete()
                        continue

                    old_sku = variant.sku
                    used_skus.discard(old_sku)
                    new_sku = _unique_sku(
                        f"ugg-golden-{slugify(model)}-{slugify(variant.size)}",
                        used_skus,
                    )
                    used_skus.add(new_sku)
                    variant.product = survivor
                    variant.color = color
                    variant.sku = new_sku
                    variant.save()

                sort_base = (
                    survivor.images.aggregate(m=Max("sort_order"))["m"] or 0
                ) + 1
                for idx, image in enumerate(donor.images.order_by("sort_order", "pk")):
                    image.product = survivor
                    image.is_primary = False
                    image.sort_order = sort_base + idx
                    image.save(update_fields=["product", "is_primary", "sort_order"])

                TelegramImport.objects.filter(product=donor).update(product=survivor)
                donor.delete()

            if not survivor.images.filter(is_primary=True).exists():
                first = survivor.images.order_by("sort_order", "pk").first()
                if first:
                    first.is_primary = True
                    first.save(update_fields=["is_primary"])

            prices = survivor.variants.filter(price__gt=0).aggregate(m=Min("price"))
            min_price = prices["m"] or survivor.base_price

            survivor.name = TARGET_NAME
            survivor.slug = TARGET_SLUG
            # уникнути unique slug conflict якщо TARGET вже зайнятий чужим
            while (
                Product.objects.filter(slug=survivor.slug)
                .exclude(pk=survivor.pk)
                .exists()
            ):
                survivor.slug = f"{TARGET_SLUG}-{survivor.pk}"
            survivor.category = footwear
            survivor.base_price = Decimal(min_price)
            survivor.is_active = True
            survivor.save()

        final = (
            Product.objects.filter(pk=survivor.pk)
            .annotate(vcount=Count("variants"), icount=Count("images"))
            .first()
        )
        colors = list(
            ProductVariant.objects.filter(product=final)
            .exclude(color=None)
            .values_list("color__name", flat=True)
            .distinct()
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"OK product={final.pk} {final.name!r} slug={final.slug} "
                f"cat={final.category.slug} base={final.base_price} "
                f"variants={final.vcount} images={final.icount} colors={colors}"
            )
        )
