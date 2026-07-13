import re
from decimal import Decimal, InvalidOperation

from .parser_types import ParsedVariant

_SIZE_LETTER = r"(?:XXS|XXXL|XXL|XL|XS|[SML])"
_PRICE_TAG_RE = re.compile(
    r"🏷️\s*(\d[\d\s]*)|(\d[\d\s]*)\s*грн",
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
    rf"^[•\-\s]*(?:✅|❌)?\s*({_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?)\s*[—–-]",
    re.IGNORECASE,
)
_SIZE_PRICE_INLINE_RE = re.compile(
    rf"^[•\-\s]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*[—–-]\s*"
    r"(?:Sold\s*Out|(\d[\d\s]*)(?:\s*грн)?)",
    re.IGNORECASE,
)
_SIZE_PRICE_SIMPLE_RE = re.compile(
    rf"^(?:✅|❌)?\s*({_SIZE_LETTER})\s*[—–-]\s*"
    r"(?:Sold\s*Out|(\d[\d\s]*)(?:\s*грн)?)\s*$",
    re.IGNORECASE,
)
_COLOR_HEADER_RE = re.compile(
    r"^(?:коричнев|чорн|біл|бежев|син|зелен|рожев|червон|сірий|леопард|молочн|кремов)",
    re.IGNORECASE,
)


def _to_decimal(raw: str) -> Decimal | None:
    cleaned = raw.replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _extract_price(text: str) -> Decimal | None:
    match = _PRICE_TAG_RE.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    return _to_decimal(raw) if raw else None


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
    return 1


def _normalize_size(raw: str) -> str:
    size = raw.strip().upper().replace(",", ".")
    if size.isdigit() or (size.replace(".", "", 1).isdigit() and size.count(".") <= 1):
        return size
    return size


def _parse_variant_line(line: str, *, color: str | None) -> ParsedVariant | None:
    stripped = line.strip()
    if not stripped or _VARIANT_SECTION_RE.match(stripped):
        return None

    sold_out = _is_sold_out(stripped)
    price = _extract_price(stripped)

    inline = _SIZE_PRICE_INLINE_RE.match(stripped) or _SIZE_PRICE_SIMPLE_RE.match(
        stripped
    )
    if inline:
        size = _normalize_size(inline.group(1))
        if sold_out and not inline.group(2):
            return ParsedVariant(
                size=size,
                price=Decimal("0"),
                stock_qty=0,
                is_available=False,
                color=color,
            )
        if inline.group(2):
            parsed_price = _to_decimal(inline.group(2))
            if parsed_price is not None:
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


def extract_variants(caption: str) -> list[ParsedVariant]:
    lines = caption.splitlines()
    variants: list[ParsedVariant] = []
    current_color: str | None = None
    pending_size_line: str | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        next_line = lines[index + 1].strip() if index + 1 < len(lines) else None
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

        if pending_size_line and "🏷️" in stripped:
            combined = f"{pending_size_line}\n{stripped}"
            variant = _parse_variant_line(combined, color=current_color)
            pending_size_line = None
            if variant:
                variants.append(variant)
            continue

        if _SIZE_LINE_RE.match(stripped) and "🏷️" not in stripped:
            if next_line and "🏷️" in next_line and not _SIZE_LINE_RE.match(next_line):
                pending_size_line = stripped
                continue

        variant = _parse_variant_line(stripped, color=current_color)
        if variant:
            variants.append(variant)
            pending_size_line = None
            continue

        if stripped.startswith("🏷️"):
            price = _extract_price(stripped)
            if price is not None:
                variants.append(
                    ParsedVariant(
                        size="ONE SIZE",
                        price=price,
                        stock_qty=1,
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
                    stock_qty=1,
                    is_available=True,
                )
            )

    return variants
