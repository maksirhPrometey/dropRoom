"""Формати варіантів з Telegram export (CSV наявність, яруси ;, дитячі роки)."""

from __future__ import annotations

import re
from decimal import Decimal

from .parser_types import ParsedVariant
from .parser_variants import (
    _extract_price,
    _is_sold_out,
    _normalize_size,
    _to_decimal,
    normalize_color_label,
)

_DASH = r"[—–\-]"
_SIZE_TOKEN_RE = re.compile(
    r"(\d{2}(?:[.,]\d)?)\s*(?:\((\d+)\s*шт\.?\))?",
    re.IGNORECASE,
)
_AVAIL_CSV_RE = re.compile(
    r"(?im)(?:у|в)\s+наявності\s*:\s*([^\n]+)",
)
_PREORDER_CSV_RE = re.compile(
    r"(?im)під\s+замовлення\s*:\s*([^\n]+)",
)
_SIZE_DASH_PRICE_RE = re.compile(
    rf"(?im)^[•\-\s🔹]*(?:✅|❌)?\s*"
    rf"(?:XXS|XXXL|XXL|XL|XS|[SML]|\d{{2}}(?:[,.]\d)?)\s*{_DASH}"
    rf".*(?:🏷️|\d[\d\s]*\s*(?:UAH|грн|₴))",
)
_KIDS_AGE_RE = re.compile(
    rf"(?im)^(\d{{1,2}}(?:\s*{_DASH}\s*\d{{1,2}})?)\s*"
    rf"рок(?:ів|и|і)\s*{_DASH}\s*(\d[\d ]*)$",
)
_TIER_SIZE_CHUNK_RE = re.compile(
    r"(\d{2}(?:\s*[,.]\s*\d)?)",
)
_AVAIL_HEADER_RE = re.compile(r"(?i)^(?:у|в)\s+наявності\s*:?\s*$")
_PREORDER_HEADER_RE = re.compile(r"(?i)^під\s+замовлення\s*:?\s*$")
_SIZE_TOKEN_RU = (
    r"(?:2ХЛ|3ХЛ|ХХЛ|ХЛ|2XL|3XL|XXL|XXS|XXXL|XL|XS|[СМЛSML])"
)
_COLOR_SIZE_LIST_RE = re.compile(
    rf"^(?P<color>[^\d,\n]+?)\s+(?P<sizes>{_SIZE_TOKEN_RU}"
    rf"(?:\s*,\s*{_SIZE_TOKEN_RU})*)\s*$"
)
_BARE_SIZE_LIST_PREORDER_RE = re.compile(
    r"(?im)^\s*(?P<sizes>\d{2}(?:[.,]\d)?(?:\s*,\s*\d{2}(?:[.,]\d)?)+)"
    r"\s+під\s+замовлення\s*$"
)


def _parse_csv_size_entries(block: str) -> list[tuple[str, int]] | None:
    """«37, 39» / «41 (2шт)» → [(size, qty)]. None якщо це не CSV-список."""
    stripped = block.strip()
    if not stripped:
        return None
    if re.search(rf"{_DASH}", stripped) and (
        "🏷️" in stripped or re.search(r"(?i)грн|uah|₴", stripped)
    ):
        return None

    entries: list[tuple[str, int]] = []
    for part in re.split(r"[,;]", stripped):
        chunk = part.strip()
        if not chunk:
            continue
        match = _SIZE_TOKEN_RE.fullmatch(chunk)
        if not match:
            # «36.5» з пробілами навколо коми всередині токена вже розбито
            soft = re.sub(r"\s+", "", chunk)
            match = _SIZE_TOKEN_RE.fullmatch(soft)
        if not match:
            continue
        size = _normalize_size(match.group(1).replace(" ", ""))
        qty = int(match.group(2)) if match.group(2) else 1
        entries.append((size, qty))

    return entries or None


def extract_stock_csv_variants(caption: str) -> list[ParsedVariant] | None:
    """
    У наявності: 37, 39
    Під замовлення: 36, 36.5, …
    🏷️8200
    """
    if len(_SIZE_DASH_PRICE_RE.findall(caption)) >= 2:
        return None

    avail_match = _AVAIL_CSV_RE.search(caption)
    preorder_match = _PREORDER_CSV_RE.search(caption)
    if not avail_match and not preorder_match:
        return None

    avail_entries = (
        _parse_csv_size_entries(avail_match.group(1)) if avail_match else None
    )
    preorder_entries = (
        _parse_csv_size_entries(preorder_match.group(1)) if preorder_match else None
    )
    if not avail_entries and not preorder_entries:
        return None

    price = _extract_price(caption)
    if price is None:
        return None

    by_size: dict[str, ParsedVariant] = {}
    for size, qty in avail_entries or []:
        by_size[size] = ParsedVariant(
            size=size,
            price=price,
            stock_qty=max(qty, 1),
            is_available=True,
        )
    for size, _qty in preorder_entries or []:
        if size in by_size:
            continue
        by_size[size] = ParsedVariant(
            size=size,
            price=price,
            stock_qty=0,
            is_available=True,
        )

    return list(by_size.values()) or None


def extract_semicolon_tier_variants(caption: str) -> list[ParsedVariant] | None:
    """
    36 ; 36,5 ; 38 🏷️5150
    44,5 ; 45 Sold out❌
    """
    variants: list[ParsedVariant] = []
    for line in caption.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ";" not in stripped:
            continue

        sold_out = _is_sold_out(stripped)
        price = _extract_price(stripped)
        if price is None and not sold_out:
            continue

        # Розміри — у лівій частині до першої ціни / Sold out
        left = re.split(r"🏷️|sold\s*out", stripped, maxsplit=1, flags=re.I)[0]
        sizes: list[str] = []
        for match in _TIER_SIZE_CHUNK_RE.finditer(left):
            raw = match.group(1).replace(" ", "").replace(",", ".")
            sizes.append(_normalize_size(raw))

        if len(sizes) < 1:
            continue

        for size in sizes:
            variants.append(
                ParsedVariant(
                    size=size,
                    price=price or Decimal("0"),
                    stock_qty=0,
                    is_available=not sold_out,
                    note=stripped,
                )
            )

    if len(variants) < 2:
        return None
    return variants


def extract_kids_age_variants(caption: str) -> list[ParsedVariant] | None:
    """2 роки — 1050 / 8-10 роки — 1230."""
    variants: list[ParsedVariant] = []
    for match in _KIDS_AGE_RE.finditer(caption):
        age_raw = re.sub(r"\s+", "", match.group(1))
        age_raw = age_raw.replace("—", "-").replace("–", "-")
        size = f"{age_raw} р."[:20]
        price = _to_decimal(match.group(2))
        if price is None:
            continue
        variants.append(
            ParsedVariant(
                size=size,
                price=price,
                stock_qty=0,
                is_available=True,
                note=match.group(0).strip(),
            )
        )

    if len(variants) < 2:
        return None
    return variants


def extract_availability_color_size_variants(caption: str) -> list[ParsedVariant] | None:
    """
    У наявності
    Біле ХЛ
    Чорне ХЛ
    🏷️3600

    Під замовлення
    Біле М, Л, 2ХЛ
    Чорне Л, ХЛ, 2ХЛ
    🏷️ 3200
    """
    variants: list[ParsedVariant] = []
    in_stock: bool | None = None
    pending: list[tuple[str | None, list[str]]] = []

    for line in caption.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _AVAIL_HEADER_RE.match(stripped):
            pending.clear()
            in_stock = True
            continue
        if _PREORDER_HEADER_RE.match(stripped):
            pending.clear()
            in_stock = False
            continue
        if in_stock is None:
            continue
        color_size = _COLOR_SIZE_LIST_RE.match(stripped)
        if color_size:
            color = normalize_color_label(color_size.group("color"))
            sizes = [
                _normalize_size(token.strip())
                for token in re.split(r"\s*,\s*", color_size.group("sizes"))
                if token.strip()
            ]
            if sizes:
                pending.append((color, sizes))
            continue
        price = _extract_price(stripped)
        if price is not None and pending:
            for color, sizes in pending:
                for size in sizes:
                    variants.append(
                        ParsedVariant(
                            size=size,
                            price=price,
                            stock_qty=1 if in_stock else 0,
                            is_available=True,
                            color=color,
                        )
                    )
            pending.clear()
            in_stock = None
            continue

    if len(variants) < 2:
        return None
    return variants


def extract_bare_size_list_preorder_variants(caption: str) -> list[ParsedVariant] | None:
    """
    ₴15,600.00 ₴10,990.00

    36, 37, 38, 39 під замовлення

    Ціна вже названа раніше в тексті — рядок з розмірами йде без неї.
    """
    match = _BARE_SIZE_LIST_PREORDER_RE.search(caption)
    if not match:
        return None
    price = _extract_price(caption)
    if price is None:
        return None
    sizes = [
        _normalize_size(part.strip())
        for part in re.split(r"\s*,\s*", match.group("sizes"))
        if part.strip()
    ]
    if len(sizes) < 2:
        return None
    return [
        ParsedVariant(size=size, price=price, stock_qty=0, is_available=True)
        for size in sizes
    ]


def extract_list_format_variants(caption: str) -> list[ParsedVariant] | None:
    """Спробувати спеціалізовані формати export; None → звичайний line-парсер."""
    for extractor in (
        extract_stock_csv_variants,
        extract_kids_age_variants,
        extract_semicolon_tier_variants,
        extract_availability_color_size_variants,
        extract_bare_size_list_preorder_variants,
    ):
        variants = extractor(caption)
        if variants:
            return variants
    return None
