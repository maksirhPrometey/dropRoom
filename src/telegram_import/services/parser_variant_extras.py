"""Додаткові формати розмірів/кольорів з caption (бот-група)."""

from __future__ import annotations

import re
from decimal import Decimal

from .parser_types import ParsedVariant
from .parser_variants import (
    _COLOR_HEADER_RE,
    _CYR_SIZE_MAP,
    _DASH,
    _extract_old_price,
    _extract_price,
    _extract_stock_qty,
    _is_sold_out,
    _normalize_size,
    _SIZE_LINE_RE,
    _STOCK_NOTE_GENERIC_RE,
    _STOCK_NOTE_RE,
    _to_decimal,
    normalize_color_label,
)
from .stock_signals import line_signals_in_stock

_SIZE_TOKEN_CAPTURE = (
    r"(?:XXS|XXXL|XXL|XL|XS|2XL|3XL|[SML]|ХХЛ|ХЛ|ХС|[СМЛсмл]|\d{2}(?:[,.]\d)?)"
)
_MULTI_SIZE_PRICE_RE = re.compile(
    rf"^(?P<prefix>.*?)"
    rf"(?P<sizes>{_SIZE_TOKEN_CAPTURE}"
    rf"(?:\s*,\s*{_SIZE_TOKEN_CAPTURE})+)\s*"
    rf"{_DASH}\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
_CYR_SIZE_PREORDER_PRICE_RE = re.compile(
    rf"^(?P<size>[смлСМЛ]|хл|ххл|ХЛ|ХХЛ|[smlSML]|xl|xxl|XS|XL|XXL)\s+"
    rf"під\s+замовлення\s+(?P<price>\d[\d\s]*)$",
    re.IGNORECASE,
)
_CYR_SIZES_BLOCK_RE = re.compile(
    r"^(?P<sizes>[смлСМЛ](?:\s*[,таіy]+\s*[смлСМЛ])+)\s+під\s+замовлення\s*$",
    re.IGNORECASE,
)
_RULER_STOCK_RE = re.compile(
    rf"^📏\s*(?P<size>\d{{2}}(?:[,.]\d)?)\s*{_DASH}\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
# «під замовлення від 39 до 45» / «від 40 до 44» — діапазон EU-розмірів
# з однією спільною ціною з caption (окремим рядком 🏷️…).
_PREORDER_SIZE_RANGE_RE = re.compile(
    r"^(?:під\s+замовленн\w*\s+)?від\s+(?P<start>\d{2}(?:[,.]\d)?)"
    r"\s+до\s+(?P<end>\d{2}(?:[,.]\d)?)\s*$",
    re.IGNORECASE,
)
_SIZE_WITH_NOTE_PRICE_RE = re.compile(
    rf"^(?P<size>\d{{2}}(?:[,.]\d)?)\s*\([^)]*\)\s*{_DASH}\s*(?P<rest>.+)$",
)
_SIZE_MEASUREMENT_TRAILING_PRICE_RE = re.compile(
    rf"^(?P<size>{_SIZE_TOKEN_CAPTURE})\s*{_DASH}\s*"
    r"(?:талія|груди|стегна|ог|обхват)\b.*?(?P<price>\d{3,6})\s*$",
    re.IGNORECASE,
)
_LABELED_SIZE_LIST_PRICE_RE = re.compile(
    r"^(?:в|у)?\s*(?:наявності|під\s+замовлення)\s+"
    rf"(?:📏\s*)?(?P<sizes>{_SIZE_TOKEN_CAPTURE}(?:\s*,\s*{_SIZE_TOKEN_CAPTURE})*)"
    rf"\s*(?:{_DASH}\s*)?(?P<rest>.+)$",
    re.IGNORECASE,
)
_BARE_SIZE_PRICE_TAG_RE = re.compile(
    rf"^(?:📏\s*)?(?P<size>{_SIZE_TOKEN_CAPTURE})\s+"
    r"(?:🏷️\s*(?P<price1>\d[\d\s]*)|(?P<price2>\d[\d\s]*)\s*(?:грн|UAH|₴))\s*$",
    re.IGNORECASE,
)
_BARE_COLOR_LIST_PRICE_RE = re.compile(
    r"^(?P<colors>[а-яіїєґ'’\s]+?)\s+(?:🏷️\s*)?(?P<price>\d{3,6})\s*(?:грн|UAH|₴)?\s*$",
    re.IGNORECASE,
)


def parse_multi_size_price_line(
    line: str, *, color: str | None = None
) -> list[ParsedVariant] | None:
    """«M, L, XL - 🏷️4350» або «Біла S, M, XL -🏷️1399»."""
    stripped = line.strip()
    if not stripped or "," not in stripped:
        return None
    match = _MULTI_SIZE_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _extract_price(match.group("rest")) or _extract_price(stripped)
    if price is None:
        return None
    prefix = (match.group("prefix") or "").strip(" -—–·|")
    sizes_raw = match.group("sizes")
    sizes = [
        _normalize_size(part.strip())
        for part in re.split(r"\s*,\s*", sizes_raw)
        if part.strip()
    ]
    if len(sizes) < 2:
        return None
    line_color = color
    if prefix:
        # «Розмір М, L, XL — …» — «Розмір» тут службове слово, а не колір;
        # _clean_color_header лише зрізає булети/«під замовлення» і не
        # відкидає такі слова, тож для кольору довіряємо лише
        # normalize_color_label (він явно відкидає «розмір»/«ціна»/тощо).
        cleaned = normalize_color_label(prefix)
        if cleaned and "," not in cleaned:
            line_color = cleaned
    sold_out = _is_sold_out(stripped)
    stock = (
        0
        if sold_out or "під замовлення" in stripped.lower()
        else _extract_stock_qty(stripped, is_available=True)
    )
    return [
        ParsedVariant(
            size=size,
            price=price,
            stock_qty=stock,
            is_available=not sold_out,
            color=line_color,
            note=stripped,
        )
        for size in sizes
    ]


def parse_cyrillic_preorder_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """«с під замовлення  4050»."""
    stripped = line.strip()
    match = _CYR_SIZE_PREORDER_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _to_decimal(match.group("price"))
    if price is None:
        return None
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=0,
        is_available=True,
        color=color,
        note=stripped,
    )


def parse_cyrillic_sizes_preorder_block(
    line: str, *, caption: str, color: str | None = None
) -> list[ParsedVariant] | None:
    """«с , м та л  під замовлення» + 🏷️ з caption."""
    stripped = line.strip()
    match = _CYR_SIZES_BLOCK_RE.match(stripped)
    if not match:
        return None
    price = _extract_price(caption)
    if price is None:
        return None
    tokens = re.split(r"[\s,таіy]+", match.group("sizes"), flags=re.I)
    sizes = [_normalize_size(tok) for tok in tokens if tok.strip()]
    sizes = [size for size in sizes if size in {"S", "M", "L", "XL", "XXL", "XS"}]
    if len(sizes) < 2:
        return None
    return [
        ParsedVariant(
            size=size,
            price=price,
            stock_qty=0,
            is_available=True,
            color=color,
            note=stripped,
        )
        for size in sizes
    ]


def parse_ruler_stock_line(
    line: str, *, caption: str, color: str | None = None
) -> ParsedVariant | None:
    """«📏38 - в наявності 1 пара» (ціна 0 → default на імпорті)."""
    stripped = line.strip()
    match = _RULER_STOCK_RE.match(stripped)
    if not match:
        return None
    price = _extract_price(stripped) or _extract_price(caption) or Decimal("0")
    rest = match.group("rest")
    sold_out = _is_sold_out(rest)
    stock = 0 if sold_out else _extract_stock_qty(rest, is_available=True)
    if not sold_out and stock == 0 and line_signals_in_stock(rest):
        stock = 1
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


def _expand_numeric_size_range(start_raw: str, end_raw: str) -> list[str] | None:
    """Розгорнути «39…45» / «39.5…42.5» у список нормалізованих розмірів."""
    try:
        start = Decimal(start_raw.replace(",", "."))
        end = Decimal(end_raw.replace(",", "."))
    except Exception:
        return None
    if start > end or (end - start) > 20:
        return None
    step = (
        Decimal("0.5")
        if (start % 1 != 0) or (end % 1 != 0)
        else Decimal("1")
    )
    sizes: list[str] = []
    current = start
    while current <= end:
        if current == current.to_integral_value():
            sizes.append(str(int(current)))
        else:
            sizes.append(format(current.normalize(), "f"))
        current += step
    return sizes if len(sizes) >= 2 else None


def parse_preorder_size_range_line(
    line: str, *, caption: str, color: str | None = None
) -> list[ParsedVariant] | None:
    """
    «під замовлення від 39 до 45» + окремо в caption «🏷️4250 замість 6900».
    Усі розміри діапазону — одна ціна, stock=0 (під замовлення).
    """
    stripped = line.strip()
    match = _PREORDER_SIZE_RANGE_RE.match(stripped)
    if not match:
        return None
    sizes = _expand_numeric_size_range(match.group("start"), match.group("end"))
    if not sizes:
        return None
    price = _extract_price(caption)
    if price is None:
        return None
    lowered = stripped.lower()
    is_preorder = "під замовлення" in lowered or "під замовлення" in caption.lower()
    sold_out = _is_sold_out(stripped)
    stock = 0 if (sold_out or is_preorder) else 1
    old_price = _extract_old_price(caption)
    compare = old_price if old_price and old_price > price else None
    return [
        ParsedVariant(
            size=size,
            price=price,
            stock_qty=stock,
            is_available=not sold_out,
            color=color,
            note=stripped,
            compare_price=compare,
        )
        for size in sizes
    ]


def parse_size_with_note_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """«35 (22,5 см) — 7250 грн» — розмір з приміткою (довжина стопи) + ціна."""
    stripped = line.strip()
    match = _SIZE_WITH_NOTE_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _extract_price(match.group("rest")) or _extract_price(stripped)
    if price is None:
        return None
    sold_out = _is_sold_out(stripped)
    stock = 0 if sold_out else _extract_stock_qty(stripped, is_available=True)
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


def parse_labeled_size_list_price_line(
    line: str, *, color: str | None = None
) -> list[ParsedVariant] | None:
    """
    «в наявності 📏S 🏷️1899» / «під замовлення хс , м , с , л 🏷️1999» —
    мітка наявності одразу перед списком розмірів, без тире.
    """
    stripped = line.strip()
    match = _LABELED_SIZE_LIST_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _extract_price(match.group("rest")) or _extract_price(stripped)
    if price is None:
        return None
    sizes = [
        _normalize_size(part.strip())
        for part in re.split(r"\s*,\s*", match.group("sizes"))
        if part.strip()
    ]
    if not sizes:
        return None
    preorder = "замовлення" in stripped.lower()
    sold_out = _is_sold_out(stripped)
    stock = 0
    if not sold_out and not preorder:
        stock = _extract_stock_qty(stripped, is_available=True) or 1
    return [
        ParsedVariant(
            size=size,
            price=price,
            stock_qty=stock,
            is_available=not sold_out,
            color=color,
            note=stripped,
        )
        for size in sizes
    ]


def parse_bare_size_price_tag_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """«39 🏷️4310» / «40 4299 грн» — розмір і ціна без тире між ними."""
    stripped = line.strip()
    match = _BARE_SIZE_PRICE_TAG_RE.match(stripped)
    if not match:
        return None
    raw_price = match.group("price1") or match.group("price2")
    price = _to_decimal(raw_price) if raw_price else None
    if price is None:
        return None
    sold_out = _is_sold_out(stripped)
    stock = 0
    if not sold_out:
        stock = _extract_stock_qty(stripped, is_available=True) or 1
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


_SIZE_FOOT_LENGTH_PRICE_RE = re.compile(
    rf"^[•▫▪◦\-\s🔹📏\uFE0F]*(?P<size>{_SIZE_TOKEN_CAPTURE})\s*"
    r"\([\d,.]+\s*см\)\s*"
    rf"{_DASH}\s*"
    r"(?:🏷️\s*)?(?P<price>\d[\d\s]*)\s*(?:грн|UAH|₴)?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


def parse_size_foot_length_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """«🔹 35 (22 см) — 4 950 грн 1 пара в наявності» — розмір із довжиною
    стопи в дужках між розміром і тире, який звичний _SIZE_LINE_RE не бачить."""
    stripped = line.strip()
    match = _SIZE_FOOT_LENGTH_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _to_decimal(match.group("price"))
    if price is None:
        return None
    sold_out = _is_sold_out(stripped)
    rest = match.group("rest") or ""
    stock = 0
    if not sold_out:
        stock = _extract_stock_qty(rest, is_available=True) or _extract_stock_qty(
            stripped, is_available=True
        ) or 1
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


_SIZE_PAREN_NOTE_PRICE_RE = re.compile(
    rf"^[•▫▪◦\-\s🔹📏\uFE0F]*(?:✅|❌)?\s*(?P<size>{_SIZE_TOKEN_CAPTURE})\s*"
    r"\([^)]*\)\s*"
    rf"(?:{_DASH}\s*)?"
    r"(?:🏷️\s*(?P<price1>\d[\d\s]*)|(?P<price2>\d[\d\s]*)\s*(?:грн|UAH|₴|гр\b)?)\s*$",
    re.IGNORECASE,
)


def parse_size_paren_note_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """
    «S (ПОГ 56см, довжина 69см, рукав 67см) 🏷️5250» — розмір-літера з
    приміткою-заміром у дужках і ціною одразу після (з тире чи без нього).
    На відміну від `_SIZE_WITH_NOTE_PRICE_RE`/`_SIZE_FOOT_LENGTH_PRICE_RE`
    (лише цифрові розміри й обов'язкове тире) тут розмір може бути літерою
    (S/M/L), а тире — необов'язкове.
    """
    stripped = line.strip()
    match = _SIZE_PAREN_NOTE_PRICE_RE.match(stripped)
    if not match:
        return None
    raw_price = match.group("price1") or match.group("price2")
    price = _to_decimal(raw_price) if raw_price else None
    if price is None:
        return None
    sold_out = _is_sold_out(stripped)
    stock = 0
    if not sold_out:
        stock = _extract_stock_qty(stripped, is_available=True) or 1
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


_BARE_SOLD_OUT_SIZE_RE = re.compile(
    rf"^[•▫▪◦\-\s🔹📏\uFE0F]*(?P<size>{_SIZE_TOKEN_CAPTURE})\s*(?P<tail>.*)$",
    re.IGNORECASE,
)


def parse_bare_sold_out_size_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """
    «L ❌Sold out» / «XL Sold Out» — розмір без тире й без ціни, лише
    позначка «немає в наявності». Ціну добере `_backfill_missing_prices`
    наприкінці `extract_variants` із сусіднього доступного варіанта.
    """
    stripped = line.strip()
    match = _BARE_SOLD_OUT_SIZE_RE.match(stripped)
    if not match:
        return None
    tail = match.group("tail").strip()
    # Хвіст має бути лише позначкою «немає» — жодних цифр (інакше це вже
    # рядок з розміром-заміром/ціною, який мають розібрати інші парсери).
    if not tail or any(ch.isdigit() for ch in tail) or len(tail) > 20:
        return None
    if not _is_sold_out(tail):
        return None
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=Decimal("0"),
        stock_qty=0,
        is_available=False,
        color=color,
        note=stripped,
    )


_NAMED_COLOR_STOCK_PRICE_RE = re.compile(
    r"^(?:\d+\s+)?(?P<color>[а-яіїєґ'’]+)\s+(?:є\s+)?в\s+наявності\s+"
    r"(?:🏷️\s*(?P<price1>\d[\d\s]*)|(?P<price2>\d[\d\s]*)\s*(?:грн|UAH|₴)?)\s*$",
    re.IGNORECASE,
)


def parse_named_color_in_stock_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """
    «1 рожева є в наявності 🏷️1820» — конкретний, названий колір із
    підтвердженою кількістю в наявності і власною ціною (яка може
    відрізнятись від загальної ціни «на всі кольори» вище).
    """
    stripped = line.strip()
    match = _NAMED_COLOR_STOCK_PRICE_RE.match(stripped)
    if not match:
        return None
    if not _COLOR_HEADER_RE.match(match.group("color")):
        return None
    color_name = normalize_color_label(match.group("color"))
    if not color_name:
        return None
    raw_price = match.group("price1") or match.group("price2")
    price = _to_decimal(raw_price) if raw_price else None
    if price is None:
        return None
    qty_match = re.match(r"^(\d+)\s+", stripped)
    stock_qty = int(qty_match.group(1)) if qty_match else 1
    return ParsedVariant(
        size="ONE SIZE",
        price=price,
        stock_qty=stock_qty,
        is_available=True,
        color=color_name,
        note=stripped,
    )


_AGE_SIZE_PRICE_RE = re.compile(
    r"^(?P<age>\d{1,2}(?:\s*[-–—]\s*\d{1,2})?)\s*(?P<unit>рік(?:ів)?|роки|років)\s*"
    r"[—–\-]\s*(?:🏷️\s*)?(?P<price>\d[\d\s]*)\s*(?:грн|UAH|₴)?\s*"
    r"[🤍🖤💛💚💙🧡❤️🤎💜\s]*$",
    re.IGNORECASE,
)


def parse_age_size_price_line(
    line: str, *, color: str | None = None
) -> ParsedVariant | None:
    """
    «2 роки - 1050», «10–12 років — 1 350 грн» — дитячий одяг, розмір за
    віком. Без цього «10–12» хибно розпізнається як звичайний числовий
    розмір «10» (як у взутті), а решта вікових рядків без тире одразу
    після числа взагалі не потрапляють у жоден варіант.
    """
    stripped = line.strip()
    match = _AGE_SIZE_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _to_decimal(match.group("price"))
    if price is None:
        return None
    age = re.sub(r"\s*[-–—]\s*", "-", match.group("age").strip())
    size = f"{age} {match.group('unit')}"[:20]
    sold_out = _is_sold_out(stripped)
    stock = 0
    if not sold_out:
        stock = _extract_stock_qty(stripped, is_available=True) or 1
    return ParsedVariant(
        size=size,
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


_COLOR_COLON_SIZE_LIST_PRICE_RE = re.compile(
    r"^(?P<color>[а-яіїєґ'’\s]+?)\s*:\s*"
    r"(?P<sizes>(?:хс|хл|ххл|[смл])(?:\s*(?:,|та|і)\s*(?:хс|хл|ххл|[смл]))*)\s+"
    r"(?:🏷️\s*)?(?P<price>\d[\d\s]*)\s*(?:грн|UAH|₴)?\s*$",
    re.IGNORECASE,
)


def parse_color_colon_size_list_price_line(
    line: str,
) -> list[ParsedVariant] | None:
    """«блакитна : с та м 🏷️1960» — колір із власним обмеженим списком
    розмірів (кир. скорочення), а не всі розміри з попередньої таблиці."""
    stripped = line.strip()
    match = _COLOR_COLON_SIZE_LIST_PRICE_RE.match(stripped)
    if not match:
        return None
    color = normalize_color_label(match.group("color"))
    if not color:
        return None
    price = _to_decimal(match.group("price"))
    if price is None:
        return None
    size_tokens = re.split(r"\s*(?:,|та|і)\s*", match.group("sizes").strip())
    sizes = [_CYR_SIZE_MAP.get(t.lower(), t.upper()) for t in size_tokens if t.strip()]
    if not sizes:
        return None
    return [
        ParsedVariant(size=size, price=price, stock_qty=1, is_available=True, color=color)
        for size in sizes
    ]


def parse_bare_color_list_price_line(
    line: str, *, color: str | None = None
) -> list[ParsedVariant] | None:
    """
    «чорна 3850» / «біла та коричнева 4050» — один чи кілька кольорів
    підряд і гола ціна в кінці рядка, без тире й без валюти.
    """
    stripped = line.strip()
    if not stripped or color is not None:
        return None
    match = _BARE_COLOR_LIST_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _to_decimal(match.group("price"))
    if price is None or price < Decimal("100"):
        return None
    parts = re.split(r"\s*,\s*|\s+(?:та|і)\s+", match.group("colors").strip())
    colors = [normalize_color_label(part) for part in parts if part.strip()]
    colors = [c for c in colors if c]
    if not colors:
        return None
    return [
        ParsedVariant(
            size="ONE SIZE",
            price=price,
            stock_qty=1,
            is_available=True,
            color=color_name,
            note=stripped,
        )
        for color_name in colors
    ]


def parse_size_measurement_trailing_price_line(
    line: str, *, color: str | None = None
) -> list[ParsedVariant] | None:
    """
    «M — талія 81–86 см ( 2 в наявності)  під замовлення немає ❌ 1650»
    «XL — талія 96–101 см 1650»

    Ціна тут — просте число в кінці рядка, без тире й без валюти.
    """
    stripped = line.strip()
    match = _SIZE_MEASUREMENT_TRAILING_PRICE_RE.match(stripped)
    if not match:
        return None
    price = _to_decimal(match.group("price"))
    if price is None:
        return None
    size = _normalize_size(match.group("size"))
    sold_out = _is_sold_out(stripped)
    stock_match = _STOCK_NOTE_RE.search(stripped) or _STOCK_NOTE_GENERIC_RE.search(stripped)
    if stock_match and int(stock_match.group(1)) > 0:
        # «під замовлення немає» тут означає лише «немає можливості
        # замовити ще» — товар уже є в наявності («2 в наявності»).
        sold_out = False
    stock = _extract_stock_qty(stripped, is_available=True) if not sold_out else 0
    return [
        ParsedVariant(
            size=size,
            price=price,
            stock_qty=stock,
            is_available=not sold_out,
            color=color,
            note=stripped,
        )
    ]


def parse_color_size_price_line(
    line: str, *, fallback_color: str | None = None
) -> ParsedVariant | None:
    """«Біла Л - 🏷️1150» — колір + один розмір + ціна."""
    stripped = line.strip()
    if not stripped or _SIZE_LINE_RE.match(stripped):
        return None
    match = re.match(
        rf"^(?P<color>.+?)\s+(?P<size>{_SIZE_TOKEN_CAPTURE})\s*{_DASH}\s*(?P<rest>.+)$",
        stripped,
        re.IGNORECASE,
    )
    if not match:
        return None
    price = _extract_price(match.group("rest")) or _extract_price(stripped)
    if price is None:
        return None
    color = normalize_color_label(match.group("color")) or fallback_color
    sold_out = _is_sold_out(stripped)
    stock = (
        0
        if sold_out or "під замовлення" in stripped.lower()
        else _extract_stock_qty(stripped, is_available=True)
    )
    return ParsedVariant(
        size=_normalize_size(match.group("size")),
        price=price,
        stock_qty=stock,
        is_available=not sold_out,
        color=color,
        note=stripped,
    )


def try_parse_extra_variant_line(
    line: str,
    *,
    caption: str,
    color: str | None,
) -> list[ParsedVariant]:
    """Спробувати всі додаткові формати для одного рядка."""
    age_size = parse_age_size_price_line(line, color=color)
    if age_size:
        return [age_size]
    measurement_trailing = parse_size_measurement_trailing_price_line(
        line, color=color
    )
    if measurement_trailing:
        return measurement_trailing
    labeled = parse_labeled_size_list_price_line(line, color=color)
    if labeled:
        return labeled
    foot_length = parse_size_foot_length_price_line(line, color=color)
    if foot_length:
        return [foot_length]
    bare_size_price = parse_bare_size_price_tag_line(line, color=color)
    if bare_size_price:
        return [bare_size_price]
    bare_color_list = parse_bare_color_list_price_line(line, color=color)
    if bare_color_list:
        return bare_color_list
    named_color_stock = parse_named_color_in_stock_price_line(line, color=color)
    if named_color_stock:
        return [named_color_stock]
    if color is None:
        colon_size_list = parse_color_colon_size_list_price_line(line)
        if colon_size_list:
            return colon_size_list
    multi = parse_multi_size_price_line(line, color=color)
    if multi:
        return multi
    size_note = parse_size_with_note_price_line(line, color=color)
    if size_note:
        return [size_note]
    paren_note_price = parse_size_paren_note_price_line(line, color=color)
    if paren_note_price:
        return [paren_note_price]
    color_size = parse_color_size_price_line(line, fallback_color=color)
    if color_size:
        return [color_size]
    cyr_line = parse_cyrillic_preorder_price_line(line, color=color)
    if cyr_line:
        return [cyr_line]
    cyr_block = parse_cyrillic_sizes_preorder_block(line, caption=caption, color=color)
    if cyr_block:
        return cyr_block
    size_range = parse_preorder_size_range_line(line, caption=caption, color=color)
    if size_range:
        return size_range
    ruler = parse_ruler_stock_line(line, caption=caption, color=color)
    if ruler:
        return [ruler]
    # Максимально загальний фолбек — лише «SIZE ❌Sold out» без жодних
    # цифр у хвості, тож пробуємо його останнім, щоб не перехопити рядки,
    # які мали розібрати точніші парсери вище.
    bare_sold_out = parse_bare_sold_out_size_line(line, color=color)
    if bare_sold_out:
        return [bare_sold_out]
    return []
