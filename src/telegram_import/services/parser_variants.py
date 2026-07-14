import re
from decimal import Decimal, InvalidOperation

from .parser_types import ParsedVariant
from .stock_signals import caption_signals_in_stock, line_signals_in_stock

_SIZE_LETTER = r"(?:XXS|XXXL|XXL|XL|XS|[SML])"
_DASH = r"[—–\-]"
_PRICE_TAG_RE = re.compile(
    r"🏷️\s*(\d[\d\s]*)|"
    r"(\d[\d\s]*)\s*(?:UAH|грн|₴)|"
    r"(\d[\d\s]*)\s*гр\b",
    re.IGNORECASE,
)
_SOLD_OUT_RE = re.compile(
    r"sold\s*out|закінчил|немає|нема\b|розпродан",
    re.IGNORECASE,
)
_STOCK_NOTE_RE = re.compile(
    r"(\d+)\s*пар[аи]?\s*(?:є\s*)?в\s*наявності",
    re.IGNORECASE,
)
_VARIANT_SECTION_RE = re.compile(
    r"^(?:📏\s*)?(?:розміри\s*(?:та\s*ціни)?|розмірна\s*сітка)\s*:?\s*$",
    re.IGNORECASE,
)
_SIZE_LINE_RE = re.compile(
    rf"^[•\-\s]*(?:✅|❌)?\s*({_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?)\s*{_DASH}",
    re.IGNORECASE,
)
_SIZE_LETTER_EU_RANGE_RE = re.compile(
    rf"^[•\-\s]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    rf"\d{{2}}(?:[,.]\d)?\s*{_DASH}\s*\d{{2}}(?:[,.]\d)?",
    re.IGNORECASE,
)
_SIZE_PRICE_INLINE_RE = re.compile(
    rf"^[•\-\s]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    r"(?:Sold\s*Out|🏷️\s*(\d[\d\s]*)|(\d[\d\s]*)(?:\s*(?:UAH|грн|₴|гр\b))?)",
    re.IGNORECASE,
)
_SIZE_PRICE_SIMPLE_RE = re.compile(
    rf"^(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    r"(?:Sold\s*Out|🏷️\s*(\d[\d\s]*)|(\d[\d\s]*)(?:\s*(?:UAH|грн|₴|гр\b))?)\s*$",
    re.IGNORECASE,
)
_SIZE_MEASUREMENT_RE = re.compile(
    rf"^(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*(?:груди|ог|обхват)",
    re.IGNORECASE,
)
_SIZE_RANGE_AFTER_DASH_RE = re.compile(
    rf"^{_DASH}\s*\d{{2}}(?:[,.]\d)?\s*{_DASH}\s*\d{{2}}",
)
_TRAILING_PRICE_RE = re.compile(
    rf"{_DASH}\s*(\d[\d\s]*)\s*(?:UAH|грн|₴|гр\b)?\s*$",
    re.IGNORECASE,
)
_COLOR_HEADER_RE = re.compile(
    r"^(?:коричнев|чорн|біл|бежев|син|зелен|рожев|червон|сірий|леопард|молочн|кремов)",
    re.IGNORECASE,
)
_MIN_BARE_PRICE = Decimal("100")


def _to_decimal(raw: str) -> Decimal | None:
    cleaned = raw.replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _extract_price(text: str) -> Decimal | None:
    matches = list(_PRICE_TAG_RE.finditer(text))
    if matches:
        # На рядках на кшталт «S — 46–48 … — 3150 UAH» беремо останню ціну.
        match = matches[-1]
        raw = next((group for group in match.groups() if group), None)
        price = _to_decimal(raw) if raw else None
        if price is not None:
            return price

    trailing = _TRAILING_PRICE_RE.search(text.strip())
    if not trailing:
        return None
    price = _to_decimal(trailing.group(1))
    if price is None:
        return None
    # Без валюти беремо лише правдоподібну ціну, не «46» з діапазону розміру.
    if _has_currency_marker(text) or price >= _MIN_BARE_PRICE:
        return price
    return None


def _has_currency_marker(text: str) -> bool:
    return "🏷️" in text or bool(
        re.search(r"(?:UAH|грн|₴)|\bгр\b", text, re.IGNORECASE)
    )


def _inline_looks_like_size_range(line: str, match: re.Match) -> bool:
    tail = line[match.end() :]
    return bool(_SIZE_RANGE_AFTER_DASH_RE.match(tail))


def _is_sold_out(text: str) -> bool:
    if "❌" in text:
        return True
    return bool(_SOLD_OUT_RE.search(text))


def _extract_stock_qty(text: str, *, is_available: bool) -> int:
    if not is_available:
        return 0
    match = _STOCK_NOTE_RE.search(text)
    if match:
        return int(match.group(1))
    if line_signals_in_stock(text):
        return 1
    return 0


def _normalize_size(raw: str) -> str:
    size = raw.strip().upper().replace(",", ".")
    if size.isdigit() or (size.replace(".", "", 1).isdigit() and size.count(".") <= 1):
        return size
    return size


def _next_nonempty_line(lines: list[str], index: int) -> str | None:
    for line in lines[index + 1 :]:
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _inline_price_raw(match: re.Match) -> str | None:
    return match.group(2) or match.group(3)


def _is_plausible_price(value: Decimal, *, has_currency_marker: bool) -> bool:
    if has_currency_marker:
        return value > 0
    return value >= _MIN_BARE_PRICE


def _parse_variant_line(line: str, *, color: str | None) -> ParsedVariant | None:
    stripped = line.strip()
    if not stripped or _VARIANT_SECTION_RE.match(stripped):
        return None

    sold_out = _is_sold_out(stripped)
    tagged_price = _extract_price(stripped)
    price = tagged_price

    if _SIZE_LETTER_EU_RANGE_RE.match(stripped) and tagged_price is None:
        return None

    inline = _SIZE_PRICE_INLINE_RE.match(stripped) or _SIZE_PRICE_SIMPLE_RE.match(
        stripped
    )
    if inline and not _SIZE_LETTER_EU_RANGE_RE.match(stripped.splitlines()[0]):
        size = _normalize_size(inline.group(1))
        raw_price = _inline_price_raw(inline)
        if sold_out and not raw_price and tagged_price is None:
            return ParsedVariant(
                size=size,
                price=Decimal("0"),
                stock_qty=0,
                is_available=False,
                color=color,
            )
        if (
            raw_price
            and tagged_price is None
            and not _inline_looks_like_size_range(stripped, inline)
        ):
            parsed_price = _to_decimal(raw_price)
            if parsed_price is not None and _is_plausible_price(
                parsed_price,
                has_currency_marker=_has_currency_marker(stripped),
            ):
                price = parsed_price

    size_match = _SIZE_LINE_RE.match(stripped)
    if not size_match and not inline:
        return None

    size = _normalize_size((inline or size_match).group(1))
    if price is None and not sold_out:
        return None
    if sold_out:
        return ParsedVariant(
            size=size,
            price=price or Decimal("0"),
            stock_qty=0,
            is_available=False,
            color=color,
            note=stripped,
        )

    return ParsedVariant(
        size=size,
        price=price,
        stock_qty=_extract_stock_qty(stripped, is_available=True),
        is_available=True,
        color=color,
        note=stripped,
    )


def _is_color_header(line: str, next_line: str | None) -> bool:
    stripped = line.strip().lstrip("•").strip()
    if not stripped or len(stripped) > 40:
        return False
    lowered = stripped.lower()
    if "розмір" in lowered or "сітка" in lowered or "📏" in stripped:
        return False
    if _SIZE_LINE_RE.match(stripped) or _VARIANT_SECTION_RE.match(stripped):
        return False
    if _extract_price(stripped):
        return False
    if stripped.endswith(":"):
        return False
    if _COLOR_HEADER_RE.match(stripped):
        return True
    if next_line and (
        _SIZE_LINE_RE.match(next_line.strip())
        or "🏷️" in next_line
    ):
        if not any(ch.isdigit() for ch in stripped) and len(stripped.split()) <= 3:
            if lowered.endswith(("і", "а", "е", "ові", "еві", "ий")):
                return True
    return False


def _should_wait_for_price_line(line: str, next_line: str | None) -> bool:
    if "🏷️" in line or _extract_price(line):
        return False
    if not _SIZE_LINE_RE.match(line):
        return False
    if not next_line:
        return False
    if _SIZE_LINE_RE.match(next_line):
        return False
    if "🏷️" in next_line or _extract_price(next_line):
        return True
    return bool(_SIZE_LETTER_EU_RANGE_RE.match(line))


def extract_variants(caption: str) -> list[ParsedVariant]:
    lines = caption.splitlines()
    variants: list[ParsedVariant] = []
    current_color: str | None = None
    pending_size_line: str | None = None
    measurement_sizes: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        next_line = _next_nonempty_line(lines, index)
        if _is_color_header(stripped, next_line):
            current_color = stripped.lstrip("•").strip()
            pending_size_line = None
            continue

        if _VARIANT_SECTION_RE.match(stripped):
            pending_size_line = None
            continue

        if "розмірна сітка" in stripped.lower():
            pending_size_line = None
            continue

        measurement_match = _SIZE_MEASUREMENT_RE.match(stripped)
        if measurement_match:
            measurement_sizes.append(_normalize_size(measurement_match.group(1)))
            pending_size_line = None
            continue

        if pending_size_line and ("🏷️" in stripped or _extract_price(stripped)):
            sold_out = _is_sold_out(pending_size_line) or _is_sold_out(stripped)
            price = _extract_price(stripped) or _extract_price(pending_size_line)
            size_match = _SIZE_LINE_RE.match(pending_size_line)
            pending_size_line = None
            if size_match and price is not None:
                size = _normalize_size(size_match.group(1))
                variants.append(
                    ParsedVariant(
                        size=size,
                        price=price,
                        stock_qty=0 if sold_out else _extract_stock_qty(
                            stripped, is_available=True
                        ),
                        is_available=not sold_out,
                        color=current_color,
                        note=stripped,
                    )
                )
            continue

        if _should_wait_for_price_line(stripped, next_line):
            pending_size_line = stripped
            continue

        variant = _parse_variant_line(stripped, color=current_color)
        if variant:
            variants.append(variant)
            pending_size_line = None
            continue

        if "🏷️" in stripped or _extract_price(stripped):
            price = _extract_price(stripped)
            if price is not None and measurement_sizes:
                stock_default = 0 if "під замовлення" in caption.lower() else 1
                stock_qty = (
                    1
                    if caption_signals_in_stock(caption)
                    else stock_default
                )
                for size in measurement_sizes:
                    variants.append(
                        ParsedVariant(
                            size=size,
                            price=price,
                            stock_qty=stock_qty,
                            is_available=True,
                            color=current_color,
                        )
                    )
                measurement_sizes.clear()
                continue

            if price is not None:
                variants.append(
                    ParsedVariant(
                        size="ONE SIZE",
                        price=price,
                        stock_qty=1 if caption_signals_in_stock(caption) else 0,
                        is_available=True,
                        color=current_color,
                    )
                )

    if measurement_sizes:
        price = _extract_price(caption)
        if price is not None:
            stock_default = 0 if "під замовлення" in caption.lower() else 1
            stock_qty = 1 if caption_signals_in_stock(caption) else stock_default
            for size in measurement_sizes:
                variants.append(
                    ParsedVariant(
                        size=size,
                        price=price,
                        stock_qty=stock_qty,
                        is_available=True,
                        color=current_color,
                    )
                )

    if not variants:
        price = _extract_price(caption)
        if price is not None:
            variants.append(
                ParsedVariant(
                    size="ONE SIZE",
                    price=price,
                    stock_qty=1 if caption_signals_in_stock(caption) else 0,
                    is_available=True,
                )
            )

    return variants
