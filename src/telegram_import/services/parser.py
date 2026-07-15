import re

from django.utils.text import slugify

from src.catalog.models import Brand, Category

from .parser_types import ParsedProduct
from .parser_variants import (
    extract_variants,
    is_color_price_line,
)

_VARIANT_SECTION_RE = re.compile(
    r"^(?:📏\s*)?(?:розміри\s*(?:та\s*ціни)?|розмірна\s*сітка|"
    r"кольор(?:и|ів)?\s*(?:та\s*ціни)?)\s*:?\s*$",
    re.IGNORECASE,
)
_BRAND_LINE_RE = re.compile(
    r"^(?:бренд|brand)\s*[:：]\s*",
    re.IGNORECASE,
)
_PHYSICAL_SIZE_RE = re.compile(
    r"^розмір\s*[:：]\s*\d",
    re.IGNORECASE,
)
_TITLE_LEAD_RE = re.compile(r"^(.+?)\s+[—–-]\s+(.+)$")

_TITLE_EMOJI_RE = re.compile(
    r"^[\s✨⭐️🌟💫📏🏷️❤️🤍🖤💛💚💙🧡🤎💜]+",
)
_TRAILING_EMOJI_RE = re.compile(
    r"[\s✨⭐️🌟💫📏🏷️❤️🤍🖤💛💚💙🧡🤎💜]+$",
)
_SKIP_TITLE_RE = re.compile(
    r"^(?:розмір|обхват|света|там де|"
    r"(?:у|в)\s+наявності\s*📏|"
    r"під\s+замовлення\s+від\s+\d|"
    r"\d{2}(?:\s*[,.]\s*\d)?\s*;|"
    r"(?:XXS|XXXL|XXL|XL|XS|[SML]|\d{2}(?:[,.]\d)?)\s*[—–\-].*(?:🏷️|\d{3,}))",
    re.IGNORECASE,
)
_STOCK_NOTE_TITLE_RE = re.compile(
    r"^(?:коричнев|чорн|біл|сірий|синій|червон|рожев|зелен|бежев|оливков).*(?:в\s+наявності|наявності\s+один)",
    re.IGNORECASE,
)
_AVAILABILITY_PREFIX_RE = re.compile(
    r"^(?:(?:у|в)\s+)?(?:наявності|під\s+замовлення)\s+"
    r"(?:[\U0001F300-\U0001FAFF\u2600-\u27BF🤍🖤💛💚💙🧡❤️🤎💜⭐️✨]+\s*)*",
    re.IGNORECASE,
)
_TITLE_FIELD_PREFIX_RE = re.compile(
    r"^(?:назва|name|title)\s*[:：]\s*",
    re.IGNORECASE,
)
_BRAND_STOPWORDS = frozenset({"the", "and", "for", "new", "york"})
_BRAND_LABEL_RE = re.compile(
    r"^(?:бренд|brand)\s*[:：]\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_GENDER_RE = re.compile(
    r"(?:стать|gender)[:\s]*(W|M|U|жіноч|чоловіч|унісекс)",
    re.IGNORECASE,
)

_CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("кардиган", "knitwear"),
    ("светр", "knitwear"),
    ("moon boot", "footwear"),
    ("moonboot", "footwear"),
    ("чобіт", "footwear"),
    ("черевик", "footwear"),
    ("босоніж", "footwear"),
    ("сандал", "footwear"),
    ("шльопанц", "footwear"),
    ("кросівк", "sneakers"),
    ("снікерс", "sneakers"),
    ("сумк", "bags"),
    ("tote", "bags"),
    ("shopper", "bags"),
    ("джинс", "denim"),
    ("куртк", "outerwear"),
    ("пальт", "outerwear"),
    ("accessor", "accessories"),
    ("легінс", "loungewear"),
    ("hoodie", "loungewear"),
    ("кепк", "accessories"),
    ("окуляр", "accessories"),
    ("сонцезахисн", "accessories"),
]


def _clean_title_line(line: str) -> str:
    cleaned = _TITLE_EMOJI_RE.sub("", line).strip()
    cleaned = _TRAILING_EMOJI_RE.sub("", cleaned).strip()
    cleaned = _TITLE_FIELD_PREFIX_RE.sub("", cleaned).strip()
    return cleaned.strip("—–-: ")


def _split_name_and_lead(line: str) -> tuple[str, str]:
    cleaned = _clean_title_line(line)
    if not cleaned:
        return "", ""

    match = _TITLE_LEAD_RE.match(cleaned)
    if not match:
        return cleaned, ""

    name, lead = match.group(1).strip(), match.group(2).strip()
    if len(name) > 80 or len(lead) < 20:
        return cleaned, ""
    return name, lead


def _normalize_title(title: str) -> str:
    cleaned = _clean_title_line(title)
    cleaned = _AVAILABILITY_PREFIX_RE.sub("", cleaned).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _extract_title(caption: str) -> str:
    for line in caption.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") or "см" in stripped.lower() and "—" in stripped:
            continue
        if _SKIP_TITLE_RE.match(stripped):
            continue
        if _STOCK_NOTE_TITLE_RE.match(stripped):
            continue
        if _BRAND_LABEL_RE.match(stripped):
            continue
        if re.match(r"^[•✅❌🔹]", stripped):
            continue
        if _VARIANT_SECTION_RE.match(stripped):
            continue
        name, _lead = _split_name_and_lead(stripped)
        title = _normalize_title(name or stripped)
        if title and len(title) > 2:
            return title[:255]
    return "Товар з Telegram"


def _line_matches_title(stripped: str, title: str) -> tuple[bool, str]:
    cleaned = _clean_title_line(stripped)
    normalized = _normalize_title(cleaned)
    title_norm = _normalize_title(title)
    if normalized == title_norm:
        return True, ""

    if cleaned == _clean_title_line(title):
        return True, ""

    name, lead = _split_name_and_lead(stripped)
    if name and name == title:
        return True, lead

    if title in cleaned:
        remainder = cleaned.split(title, 1)[1].lstrip(" —–-: ")
        if remainder and remainder != cleaned:
            return True, remainder
        return True, ""

    return False, ""


def _extract_description(caption: str, title: str) -> str:
    lines = caption.splitlines()
    description_lines: list[str] = []
    title_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if description_lines:
                description_lines.append("")
            continue

        if not title_found:
            matched, lead = _line_matches_title(stripped, title)
            if matched:
                title_found = True
                if lead:
                    description_lines.append(lead)
            continue

        if _BRAND_LINE_RE.match(stripped):
            continue
        if _VARIANT_SECTION_RE.match(stripped):
            break
        if is_color_price_line(stripped):
            break
        if stripped.startswith("•") and "🏷️" in stripped:
            break
        if re.match(r"^[✅❌🔹]?\s*(?:XXS|XXXL|XXL|XL|XS|[SML]|\d{2})\s*[—–-]", stripped):
            break
        if stripped.startswith("🏷️") and len(description_lines) > 0:
            break
        if _is_probable_color_header(stripped) and not _PHYSICAL_SIZE_RE.match(stripped):
            break

        description_lines.append(stripped)

    cleaned_lines = [
        line
        for line in description_lines
        if line and not _BRAND_LINE_RE.match(line)
    ]
    description = "\n".join(cleaned_lines).strip()
    return description or caption.strip()


def _is_probable_color_header(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) > 40 or "🏷️" in stripped:
        return False
    lowered = stripped.lower()
    color_words = (
        "коричнев",
        "чорн",
        "біл",
        "леопард",
        "бежев",
        "сині",
        "чорні",
        "коричневі",
    )
    return any(word in lowered for word in color_words) and not stripped.startswith("•")


def _parse_gender(text: str, default: str) -> str:
    match = _GENDER_RE.search(text)
    if not match:
        return default
    value = match.group(1).lower()
    if value in {"w", "жіноч"}:
        return "W"
    if value in {"m", "чоловіч"}:
        return "M"
    return "U"


def _extract_brand_label(text: str) -> str:
    match = _BRAND_LABEL_RE.search(text)
    if not match:
        return ""
    return match.group(1).strip(" .·-|")


def _match_brand_name(name: str) -> Brand | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    exact = Brand.objects.filter(is_active=True, name__iexact=cleaned).first()
    if exact:
        return exact
    return _match_brand_in_text(cleaned)


def _match_brand_in_text(text: str) -> Brand | None:
    lowered = text.lower()
    brands = list(Brand.objects.filter(is_active=True))
    brands.sort(key=lambda brand: len(brand.name), reverse=True)

    for brand in brands:
        name = brand.name.lower()
        if name in lowered:
            return brand

        tokens = [token for token in name.replace("-", " ").split() if len(token) > 2]
        if len(tokens) >= 2 and all(token in lowered for token in tokens[-2:]):
            return brand

        if tokens:
            lead = tokens[0]
            if lead not in _BRAND_STOPWORDS and re.search(
                rf"(?<![a-zа-яіїєґ]){re.escape(lead)}(?![a-zа-яіїєґ])",
                lowered,
            ):
                return brand

    return None


def _match_brand(text: str) -> Brand | None:
    label = _extract_brand_label(text)
    if label:
        branded = _match_brand_name(label)
        if branded:
            return branded
    return _match_brand_in_text(text)


def resolve_brand(
    text: str,
    *,
    create_missing: bool = False,
) -> Brand | None:
    """Знайти бренд у caption; опційно створити з рядка «Бренд: …»."""
    label = _extract_brand_label(text)
    if label:
        existing = _match_brand_name(label)
        if existing:
            return existing
        if create_missing:
            slug_base = slugify(label) or "brand"
            slug = slug_base
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(name__iexact=label).exists():
                slug = f"{slug_base}-{counter}"
                counter += 1
            brand, _ = Brand.objects.get_or_create(
                name=label[:120],
                defaults={"slug": slug, "is_active": True},
            )
            if not brand.is_active:
                brand.is_active = True
                brand.save(update_fields=["is_active"])
            return brand

    return _match_brand_in_text(text)


def _match_category(text: str) -> Category | None:
    lowered = text.lower()
    for keyword, slug in _CATEGORY_KEYWORDS:
        if keyword in lowered:
            category = Category.objects.filter(slug=slug).first()
            if category:
                return category
    for category in Category.objects.all():
        if category.name.lower() in lowered or category.slug in lowered:
            return category
    return None


def parse_caption(
    caption: str,
    *,
    default_brand: Brand | None,
    default_category: Category | None,
    default_gender: str,
) -> ParsedProduct:
    normalized = caption.strip()
    name = _extract_title(normalized)
    description = _extract_description(normalized, name)
    brand = resolve_brand(normalized) or default_brand
    category = _match_category(normalized) or default_category
    gender = _parse_gender(normalized, default_gender)
    variants = extract_variants(normalized)

    return ParsedProduct(
        name=name,
        description=description,
        brand=brand,
        category=category,
        gender=gender,
        variants=variants,
    )
