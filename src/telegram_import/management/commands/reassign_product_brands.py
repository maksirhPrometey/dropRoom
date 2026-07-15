"""Масове перепризначення brand для всіх товарів (прибрати помилковий Crocs)."""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from src.catalog.models import Brand, Product
from src.catalog.seed_data import BRANDS
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.parser import resolve_brand

_FALLBACK_SLUGS = frozenset({"crocs", "unbranded"})


def _word_in_text(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    return bool(
        re.search(
            rf"(?<![a-zа-яіїєґ0-9]){re.escape(needle)}(?![a-zа-яіїєґ0-9])",
            haystack,
            flags=re.IGNORECASE,
        )
    )


def ensure_seed_brands() -> int:
    created = 0
    for name, slug, country in BRANDS:
        _, was_created = Brand.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "country": country or "", "is_active": True},
        )
        if was_created:
            created += 1
    return created


def materialize_brands_mentioned(text: str) -> None:
    """Створити з seed будь-який бренд, що згадується в тексті (крім crocs/unbranded)."""
    lowered = text.lower()
    for name, slug, country in sorted(BRANDS, key=lambda row: len(row[0]), reverse=True):
        if slug in _FALLBACK_SLUGS:
            continue
        if _word_in_text(name, lowered) or _word_in_text(slug.replace("-", " "), lowered):
            Brand.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "country": country or "", "is_active": True},
            )


def _best_caption(product: Product) -> str:
    captions = list(
        TelegramImport.objects.filter(product=product)
        .exclude(raw_caption="")
        .values_list("raw_caption", flat=True)
    )
    if not captions:
        return ""
    return max(captions, key=len)


def _resolve_for_product(product: Product) -> Brand | None:
    parts = [product.name or "", product.subtitle or "", _best_caption(product)]
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        return None

    materialize_brands_mentioned(text)
    brand = resolve_brand(text, create_missing=False)
    if brand and brand.slug in _FALLBACK_SLUGS:
        # Crocs лише якщо явно в тексті
        if not _word_in_text(brand.name, text) and not _word_in_text("crocs", text):
            return None
    return brand


def _unbranded() -> Brand:
    brand, _ = Brand.objects.get_or_create(
        slug="unbranded",
        defaults={"name": "Без бренду", "country": "", "is_active": True},
    )
    return brand


class Command(BaseCommand):
    help = (
        "Для ВСІХ товарів: seed брендів + визначити brand з name/caption. "
        "Помилковий Crocs без згадки в тексті → «Без бренду» або правильний бренд."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише план",
        )
        parser.add_argument(
            "--only-crocs",
            action="store_true",
            help="Лише товари з brand=crocs (швидше)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_crocs = options["only_crocs"]

        seeded = ensure_seed_brands()
        self.stdout.write(f"Seed brands: +{seeded} нових (усі з seed_data)")

        qs = Product.objects.select_related("brand").order_by("pk")
        if only_crocs:
            qs = qs.filter(brand__slug="crocs")

        scanned = 0
        updated = 0
        to_unbranded = 0
        unchanged = 0

        unbranded = _unbranded()

        for product in qs.iterator():
            scanned += 1
            resolved = _resolve_for_product(product)
            current_slug = product.brand.slug if product.brand_id else ""

            if resolved is not None:
                if product.brand_id == resolved.pk:
                    unchanged += 1
                    continue
                new_brand = resolved
            elif current_slug == "crocs":
                # Немає match у тексті — прибрати фейковий Crocs
                new_brand = unbranded
                to_unbranded += 1
            else:
                unchanged += 1
                continue

            updated += 1
            preview = (
                f"product {product.pk}: {product.brand.name} → {new_brand.name} | "
                f"{(product.name or '')[:60]!r}"
            )
            if dry_run:
                self.stdout.write(preview)
                continue

            with transaction.atomic():
                product.brand = new_brand
                product.save(update_fields=["brand"])
                if new_brand.slug != "unbranded" and not product.is_active:
                    product.is_active = True
                    product.save(update_fields=["is_active"])
            self.stdout.write(self.style.SUCCESS(preview))

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{' (dry-run)' if dry_run else ''}: "
                f"переглянуто {scanned}, оновлено {updated} "
                f"(з них → Без бренду: {to_unbranded}), без змін {unchanged}"
            )
        )
