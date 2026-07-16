import re

from django.utils.text import slugify

from src.catalog.models import Brand, Category

from .parser_types import ParsedProduct
from .parser_variants import (
    extract_variants,
    is_color_price_line,
    looks_like_variant_line,
)

_VARIANT_SECTION_RE = re.compile(
    # «Розміри:» саме собою — майже завжди фізичні виміри товару (сумки),
    # не таблиця розмір↔ціна; вимагаємо «та ціни» щоб не зрізати опис.
    r"^(?:📏\s*)?(?:розміри\s+та\s*ціни|розмірна\s*сітка|"
    r"кольор(?:и|ів)?\s*(?:та\s*ціни)?)\s*:?\s*$",
    re.IGNORECASE,
)
_BRAND_LINE_RE = re.compile(
    r"^(?:бренд|brand)\s*[:：]\s*",
    re.IGNORECASE,
)
_DESCRIPTION_LABEL_RE = re.compile(
    r"^(?:опис|description)\s*[:：]\s*$",
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
    ("шльопанц", "footwear"),
    ("clog", "footwear"),
    ("клог", "footwear"),
    ("кросівк", "sneakers"),
    ("снікерс", "sneakers"),
    ("кед", "sneakers"),
    ("худі", "loungewear"),
    ("hoodie", "loungewear"),
    ("костюм", "loungewear"),
    ("легінс", "loungewear"),
    ("лосин", "loungewear"),
    ("велосипедк", "loungewear"),
    ("шорт", "loungewear"),
    ("білизн", "loungewear"),
    ("куртк", "outerwear"),
    ("пальт", "outerwear"),
    ("пуховик", "outerwear"),
    ("жилет", "outerwear"),
    ("безрукав", "outerwear"),
    ("блейзер", "outerwear"),
    ("бомбер", "outerwear"),
    ("вітрівк", "outerwear"),
    ("сукн", "dresses"),
    ("сарафан", "dresses"),
    ("dress", "dresses"),
    ("футболк", "tops"),
    ("поло", "tops"),
    ("сорочк", "tops"),
    ("лонгслів", "tops"),
    ("кардиган", "knitwear"),
    ("cardigan", "knitwear"),
    ("светр", "knitwear"),
    ("світшот", "knitwear"),
    ("джемпер", "knitwear"),
    ("кофт", "knitwear"),
    ("рюкзак", "bags"),
    ("backpack", "bags"),
    ("сумк", "bags"),
    ("tote", "bags"),
    ("shopper", "bags"),
    ("шопер", "bags"),
    ("джінс", "denim"),
    ("джинс", "denim"),
    ("accessor", "accessories"),
    ("аксесуар", "accessories"),
    ("шарф", "accessories"),
    ("scarf", "accessories"),
    ("кепк", "accessories"),
    ("бейсболк", "accessories"),
    ("панамк", "accessories"),
    ("окуляр", "accessories"),
    ("sunglasses", "accessories"),
    ("сонцезахисн", "accessories"),
    ("годинник", "accessories"),
    ("ремін", "accessories"),
    ("шкарпет", "accessories"),
    ("moon boot", "footwear"),
    ("moonboot", "footwear"),
    ("чобіт", "footwear"),
    ("черевик", "footwear"),
    ("босоніж", "footwear"),
    ("сандал", "footwear"),
    ("сапог", "footwear"),
    ("балетк", "footwear"),
    ("сабо", "footwear"),
    ("мюлі", "footwear"),
    ("капц", "footwear"),
    ("слайд", "footwear"),
    ("лофер", "footwear"),
    ("єтнамк", "footwear"),
    ("trainer", "sneakers"),
    ("sneaker", "sneakers"),
    ("slide", "footwear"),
    ("штани", "loungewear"),
    ("брюк", "loungewear"),
    ("повʼязк", "accessories"),
    ("повязк", "accessories"),
    ("headband", "accessories"),
    ("bag", "bags"),
    ("phone case", "accessories"),
    ("bottle", "accessories"),
]

# Бренд/модель без жодного слова-типу товару («Adidas Vento XLG White»,
# «New Balance 2002R») найчастіше зустрічається саме в постах з кросівками:
# розміри там — суцільно числа у типовому євро-діапазоні взуття.
_SHOE_SIZE_RE = re.compile(r"^\d{2}(?:[.,]5)?$")


def _looks_like_shoe_sizes(variants: list) -> bool:
    sizes = {v.size for v in variants if v.size and v.size != "ONE SIZE"}
    if len(sizes) < 2:
        return False
    shoe_like = [s for s in sizes if _SHOE_SIZE_RE.match(s.replace(",", "."))]
    if len(shoe_like) < max(2, int(len(sizes) * 0.6)):
        return False
    return all(34 <= float(s.replace(",", ".")) <= 47 for s in shoe_like)

# Підписи бренду в caption → канонічна name з Brand/seed.
_BRAND_ALIASES: dict[str, str] = {
    "levis": "Levi's",
    "levi's": "Levi's",
    "levi’s": "Levi's",
    "левіс": "Levi's",
    "maison margiela": "Maison Margiela",
    "margiela": "Maison Margiela",
    "totême": "Toteme",
    "toteme": "Toteme",
}


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
        name, lead = _split_name_and_lead(stripped)
        title = _normalize_title(name or stripped)
        if not lead and len(title) > 100:
            # Немає ані тире, ані короткої назви — весь опис товару написаний
            # одним реченням в один рядок («Стьобаний жилет COS у …. Легка
            # утеплена модель…»). Беремо лише перше речення як назву, решта
            # піде в description через _line_matches_title (title in cleaned).
            first = _first_sentence(title)
            if 15 <= len(first) < len(title):
                title = first
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
        if _DESCRIPTION_LABEL_RE.match(stripped):
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
        # Будь-який рядок, який `extract_variants` уже розпізнає як
        # розмір/колір/ціну (в т.ч. розширені формати з
        # parser_variant_extras) — не повинен лишатись продубльованим
        # текстом в описі. Спрацьовує навіть на першому рядку після
        # заголовка — інакше опис лишиться порожнім і впаде у фолбек
        # «весь caption цілком» (рядок нижче: `description or caption`).
        if looks_like_variant_line(stripped, caption=caption):
            break

        description_lines.append(stripped)

    cleaned_lines = [
        line
        for line in description_lines
        if line and not _BRAND_LINE_RE.match(line) and not _DESCRIPTION_LABEL_RE.match(line)
    ]
    description = "\n".join(cleaned_lines).strip()
    if description:
        return description
    if title_found:
        # Заголовок знайшли, а все, що йде після нього — розміри/ціни
        # (жодного вільного тексту немає). Порожній опис тут коректніший,
        # ніж дублювати всю таблицю розмірів/цін ще раз текстом.
        return ""
    return caption.strip()


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
    alias = _BRAND_ALIASES.get(cleaned.lower())
    if alias:
        cleaned = alias
    exact = Brand.objects.filter(is_active=True, name__iexact=cleaned).first()
    if exact:
        return exact
    return _match_brand_in_text(cleaned)


def _match_brand_in_text(text: str) -> Brand | None:
    lowered = text.lower()
    for alias, canonical in sorted(_BRAND_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(
            rf"(?<![a-zа-яіїєґ0-9]){re.escape(alias)}(?![a-zа-яіїєґ0-9])",
            lowered,
        ):
            brand = Brand.objects.filter(is_active=True, name__iexact=canonical).first()
            if brand:
                return brand

    brands = list(Brand.objects.filter(is_active=True))
    brands.sort(key=lambda brand: len(brand.name), reverse=True)

    for brand in brands:
        # Не підставляти Crocs/unbranded «мовчки» — лише явна згадка
        if brand.slug in {"crocs", "unbranded"}:
            name = brand.name.lower()
            if name not in lowered and brand.slug not in lowered:
                continue

        name = brand.name.lower()
        if re.search(
            rf"(?<![a-zа-яіїєґ0-9]){re.escape(name)}(?![a-zа-яіїєґ0-9])",
            lowered,
        ):
            return brand

        tokens = [token for token in name.replace("-", " ").split() if len(token) > 2]
        if len(tokens) >= 2 and all(
            re.search(
                rf"(?<![a-zа-яіїєґ0-9]){re.escape(token)}(?![a-zа-яіїєґ0-9])",
                lowered,
            )
            for token in tokens[-2:]
        ):
            return brand

        if tokens:
            lead = tokens[0]
            if lead not in _BRAND_STOPWORDS and re.search(
                rf"(?<![a-zа-яіїєґ0-9]){re.escape(lead)}(?![a-zа-яіїєґ0-9])",
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


def _first_sentence(text: str) -> str:
    match = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return match[0] if match else text


def _match_category(text: str) -> Category | None:
    """Категорія лише за ключовими словами / легітимним slug.

    Category з іменем/slug як у Brand (напр. помилковий «Sandro») — ігноруємо.
    """
    lowered = text.lower()
    for keyword, slug in _CATEGORY_KEYWORDS:
        # Ліва межа слова обов'язкова: без неї короткі англ. ключові слова
        # («tote», «bag», «dress») ловлять збіги посередині інших слів —
        # напр. «dress» в «address». «tote» додатково не має збігатись як
        # префікс бренду «Toteme».
        pattern = re.escape(keyword)
        if keyword == "tote":
            pattern += r"(?!me)"
        if re.search(rf"(?<![a-zа-яіїєґ0-9]){pattern}", lowered):
            category = Category.objects.filter(slug=slug).first()
            if category:
                return category

    brand_slugs = {
        slug.lower()
        for slug in Brand.objects.filter(is_active=True).values_list("slug", flat=True)
        if slug
    }
    brand_names = {
        name.lower()
        for name in Brand.objects.filter(is_active=True).values_list("name", flat=True)
        if name
    }

    for category in Category.objects.all():
        slug = (category.slug or "").lower()
        name = (category.name or "").lower()
        if slug in brand_slugs or name in brand_names:
            continue
        if name and re.search(rf"(?<![a-zа-яіїєґ0-9]){re.escape(name)}", lowered):
            return category
        if slug and re.search(rf"(?<![a-zа-яіїєґ0-9]){re.escape(slug)}", lowered):
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
    # Спершу шукаємо за ключовим словом у назві. Якщо там нічого немає —
    # перше речення опису (де завжди називається сам товар: «Стильний
    # кардиган…»), а вже потім увесь опис як останній резерв: пізніші
    # речення часто лише радять, з чим товар «поєднується» («…з джинсами,
    # шортами…»), і ці слова не повинні переважати над реальною категорією.
    # Повний caption НЕ використовуємо — деякі повідомлення містять
    # «приклеєний» другий товар після блоку з цінами.
    variants = extract_variants(normalized)
    category = (
        _match_category(name)
        or _match_category(_first_sentence(description))
        or _match_category(description)
    )
    if not category and _looks_like_shoe_sizes(variants):
        category = Category.objects.filter(slug="footwear").first()
    category = category or default_category
    gender = _parse_gender(normalized, default_gender)

    return ParsedProduct(
        name=name,
        description=description,
        brand=brand,
        category=category,
        gender=gender,
        variants=variants,
    )
