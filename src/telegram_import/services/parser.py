import re

from src.catalog.models import Brand, Category

from .parser_types import ParsedProduct
from .parser_variants import extract_variants

_VARIANT_SECTION_RE = re.compile(
    r"^(?:розміри\s*(?:та\s*ціни)?|розмірна\s*сітка)\s*:?\s*$",
    re.IGNORECASE,
)

_TITLE_EMOJI_RE = re.compile(
    r"^[\s✨⭐️🌟💫📏🏷️❤️🤍🖤💛💚💙🧡]+",
)
_TRAILING_EMOJI_RE = re.compile(
    r"[\s✨⭐️🌟💫📏🏷️❤️🤍🖤💛💚💙🧡]+$",
)
_SKIP_TITLE_RE = re.compile(
    r"^(?:розмір|обхват|света|там де)",
    re.IGNORECASE,
)
_GENDER_RE = re.compile(
    r"(?:стать|gender)[:\s]*(W|M|U|жіноч|чоловіч|унісекс)",
    re.IGNORECASE,
)

_CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("кардиган", "knitwear"),
    ("светр", "knitwear"),
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
]


def _clean_title_line(line: str) -> str:
    cleaned = _TITLE_EMOJI_RE.sub("", line).strip()
    cleaned = _TRAILING_EMOJI_RE.sub("", cleaned).strip()
    return cleaned.strip("—–-: ")


def _extract_title(caption: str) -> str:
    for line in caption.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") or "см" in stripped.lower() and "—" in stripped:
            continue
        if _SKIP_TITLE_RE.match(stripped):
            continue
        if re.match(r"^[•✅❌]", stripped):
            continue
        if _VARIANT_SECTION_RE.match(stripped):
            continue
        title = _clean_title_line(stripped)
        if title and len(title) > 2:
            return title[:255]
    return "Товар з Telegram"


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
            if _clean_title_line(stripped) == _clean_title_line(title) or title in stripped:
                title_found = True
            continue

        if _VARIANT_SECTION_RE.match(stripped):
            break
        if stripped.startswith("•") and "🏷️" in stripped:
            break
        if re.match(r"^[✅❌]?\s*(?:XXS|XXXL|XXL|XL|XS|[SML]|\d{2})\s*[—–-]", stripped):
            break
        if stripped.startswith("🏷️") and len(description_lines) > 0:
            break
        if _is_probable_color_header(stripped):
            break

        description_lines.append(stripped)

    description = "\n".join(line for line in description_lines if line).strip()
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


def _match_brand(text: str) -> Brand | None:
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
        if len(tokens) == 1 and tokens[0] in lowered:
            return brand

    return None


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
    brand = _match_brand(normalized) or default_brand
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
