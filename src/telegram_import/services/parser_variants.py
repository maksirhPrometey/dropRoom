import re
from decimal import Decimal, InvalidOperation

from .parser_types import ParsedVariant
from .stock_signals import caption_signals_in_stock, line_signals_in_stock

_SIZE_LETTER = r"(?:XXS|XXXL|XXL|XL|XS|2XL|3XL|[SML]|ХХЛ|ХЛ|ХС|[СМЛсмл])"
_DASH = r"[—–\-]"
_CYR_SIZE_MAP = {
    "с": "S",
    "c": "S",
    "м": "M",
    "m": "M",
    "л": "L",
    "l": "L",
    "хл": "XL",
    "ххл": "XXL",
    "xs": "XS",
    "xxs": "XXS",
    "xl": "XL",
    "xxl": "XXL",
    "2xl": "2XL",
    "3xl": "3XL",
    "s": "S",
    "m": "M",
    "l": "L",
    "2хл": "2XL",
    "3хл": "3XL",
    "хс": "XS",
    # «Х» (кирилиця) + «s»/«l» (латиниця) — поширена помилка набору тексту,
    # коли автор перемикає розкладку лише на половину слова.
    "хs": "XS",
    "хl": "XL",
    "хxl": "XXL",
}
_PRICE_TAG_RE = re.compile(
    r"🏷️\s*(\d[\d\s]*)|"
    r"(\d[\d\s]*)\s*(?:UAH|грн|₴)|"
    r"(\d[\d\s]*)\s*гр\b|"
    r"₴\s*(\d[\d\s,]*(?:\.\d+)?)",
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
_STOCK_NOTE_GENERIC_RE = re.compile(
    r"(\d+)\s*(?:шт\.?\s*)?в\s*наявності",
    re.IGNORECASE,
)
_VARIANT_SECTION_RE = re.compile(
    # «Розміри:» саме собою — майже завжди фізичні виміри товару (сумки),
    # не таблиця розмір↔ціна; вимагаємо «та ціни» щоб не зрізати опис.
    # «💰 Ціни:» (голе, без «розміри»/«кольори» попереду) — окремий,
    # самодостатній заголовок секції з ціною/розміром.
    r"^(?:📏|💰|🏷️)?\s*(?:розміри\s+та\s*ціни|розмірна\s*сітка|"
    r"кольор(?:и|ів)?\s*(?:та\s*ціни)?|ціни)\s*:?\s*$",
    re.IGNORECASE,
)
# «В наявності» / «Під замовлення» голим окремим рядком — перемикач
# контексту наявності для розмірів, які йдуть далі (до наступного такого
# перемикача), коли в одному капшені є ОБИДВА блоки з однаковою ціною.
_AVAILABILITY_CONTEXT_RE = re.compile(r"^(?:у|в)\s+наявності\s*$", re.IGNORECASE)
_PREORDER_CONTEXT_RE = re.compile(r"^під\s+замовленн\w*\s*$", re.IGNORECASE)
# «зелена лінза 4 штуки» / «коричнева 2 штуки» — колір із кількістю на
# власному рядку, без ціни; ціна на два (і більше) таких кольори одразу —
# окремим рядком нижче («…одна ціна 🏷️4550»).
_COLOR_STOCK_LINE_RE = re.compile(
    r"^(?:(?:у|в)\s+наявності\s+)?(?P<color>[а-яіїєґ'’]+)(?:\s+\S+)?\s+"
    r"(?P<qty>\d+)\s*(?:штук[аи]?|пар[аи]?)\s*$",
    re.IGNORECASE,
)
# «чорні , рожеві та білі в одну ціну» — розміри/ціни вже розібрані вище
# без кольору; тут лише перелік кольорів, доступних за тією ж сіткою цін.
_NAMED_COLORS_SHARED_PRICE_RE = re.compile(
    r"(?im)^(?P<colors>[а-яіїєґ'’\s,]+?)\s+в\s+одну\s+ціну\s*$"
)
# «Всі 5 кольорів 🏷️1780» — кольори не названо, тож окремий безколірний
# варіант з такого рядка створювати не варто (нижче майже завжди йде
# конкретний названий колір зі своєю ціною); лишаємо лише як запасний
# варіант — кінцевий фолбек функції все одно бере останню ціну з caption.
_ALL_COLORS_GENERIC_PRICE_RE = re.compile(
    r"(?i)^вс[іе]\s+\d+\s+кольор\w*\s+(?:🏷️\s*)?\d[\d\s]*\s*(?:грн|UAH|₴)?\s*$"
)
# «Розміри: XS, S, M, L, XL» — список розмірів для поточного кольору
# (заголовок кольору вище, ціна на спільна для всіх цих розмірів рядком
# нижче) — інший запис того самого «measurement_sizes» механізму.
_SIZE_LIST_LABEL_RE = re.compile(
    r"(?i)^розмір[иа]\s*:\s*(?P<sizes>.+)$"
)
_BULLET_CLASS = "•\\-\\s🔹📏▫▪◦\uFE0F"
_COLOR_EMOJI_PREFIX_RE = re.compile(
    r"^[•\-▫▪◦\s]*(?:[\U0001F300-\U0001FAFF\u2600-\u27BF"
    r"🤍🖤💛💚💙🧡❤️🤎💜🟡⚪🔴🔵🟢\uFE0F]+\s*)+",
)
# «Молочний 🤍» — той самий емодзі-набір, але в кінці назви кольору.
_COLOR_EMOJI_SUFFIX_RE = re.compile(
    r"\s*(?:[\U0001F300-\U0001FAFF\u2600-\u27BF"
    r"🤍🖤💛💚💙🧡❤️🤎💜🟡⚪🔴🔵🟢\uFE0F]+\s*)+$",
)
_SIZE_TOKEN_ONLY_RE = re.compile(
    rf"^(?:{_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?)$",
    re.IGNORECASE,
)
_SIZE_LINE_RE = re.compile(
    rf"^[{_BULLET_CLASS}]*(?:✅|❌)?\s*({_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?)\s*{_DASH}",
    re.IGNORECASE,
)
_SIZE_LETTER_EU_RANGE_RE = re.compile(
    rf"^[{_BULLET_CLASS}]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    rf"\d{{2}}(?:[,.]\d)?\s*{_DASH}\s*\d{{2}}(?:[,.]\d)?",
    re.IGNORECASE,
)
_SIZE_PRICE_INLINE_RE = re.compile(
    rf"^[{_BULLET_CLASS}]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    r"(?:Sold\s*Out|🏷️\s*(\d[\d\s]*)|(\d[\d\s]*)(?:\s*(?:UAH|грн|₴|гр\b))?)",
    re.IGNORECASE,
)
_SIZE_PRICE_SIMPLE_RE = re.compile(
    rf"^(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*"
    r"(?:Sold\s*Out|🏷️\s*(\d[\d\s]*)|(\d[\d\s]*)(?:\s*(?:UAH|грн|₴|гр\b))?)\s*$",
    re.IGNORECASE,
)
_SIZE_MEASUREMENT_RE = re.compile(
    rf"^[{_BULLET_CLASS}]*(?:✅|❌)?\s*({_SIZE_LETTER})\s*{_DASH}\s*(?:груди|ог|обхват)",
    re.IGNORECASE,
)
# «6,5US - 37 - 23,5 см» — розмір взуття у трьох системах (US - EU - см
# стопи); беремо середнє (EU) значення як канонічний розмір.
_SIZE_US_EU_CM_RE = re.compile(
    rf"^\d+(?:[,.]\d+)?\s*US\s*{_DASH}\s*(?P<size>\d{{2}}(?:[,.]\d)?)\s*{_DASH}\s*"
    r"[\d,.]+\s*см\s*$",
    re.IGNORECASE,
)
_SIZE_RANGE_AFTER_DASH_RE = re.compile(
    rf"^{_DASH}\s*\d{{2}}(?:[,.]\d)?\s*{_DASH}\s*\d{{2}}",
)
_SIZE_FOOT_LENGTH_ONLY_RE = re.compile(
    rf"^[{_BULLET_CLASS}]*(?:✅|❌)?\s*({_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?)\s*"
    r"\([\d,.]+\s*см\)\s*$",
    re.IGNORECASE,
)
# «📏 В наявності: 40 (устілка 26 см) 1 пара» — розмір із довжиною стопи в
# описовому реченні, коли ціна взагалі на іншому рядку далі по тексту й
# рядкова прив'язка через pending_size_line до неї «не дотягується».
_CAPTION_WIDE_FOOT_LENGTH_SIZE_RE = re.compile(
    r"(\d{2}(?:[,.]\d)?)\s*\((?:устілка\s*)?[\d,.]+\s*см\)",
    re.IGNORECASE,
)
# «1 в наявності 38 розмір ( 24 см )» — розмір названо просто в реченні про
# наявність, а не в окремому рядку-варіанті; ціна — окремим бланком рядком
# нижче («5499»), тож звичний pending_size_line її не підхоплює. Розмір може
# стояти як ПЕРЕД словом «розмір» («38 розмір»), так і ПІСЛЯ нього
# («в наявності розмір S») — підтримуємо обидва порядки.
_CAPTION_WIDE_SIZE_MENTION_RE = re.compile(
    rf"(?:(\d{{2}}(?:[,.]\d)?)\s*розмір|розмір\s+({_SIZE_LETTER}|\d{{2}}(?:[,.]\d)?))",
    re.IGNORECASE,
)

def _wide_size_from_caption(caption: str) -> str | None:
    foot_length_match = _CAPTION_WIDE_FOOT_LENGTH_SIZE_RE.search(caption)
    if foot_length_match:
        return _normalize_size(foot_length_match.group(1))
    size_mention_match = _CAPTION_WIDE_SIZE_MENTION_RE.search(caption)
    if size_mention_match:
        raw_size = size_mention_match.group(1) or size_mention_match.group(2)
        return _normalize_size(raw_size)
    return None
_TRAILING_PRICE_RE = re.compile(
    rf"{_DASH}\s*(\d[\d\s]*)\s*(?:UAH|грн|₴|гр\b)?\s*$",
    re.IGNORECASE,
)
_COLOR_HEADER_RE = re.compile(
    r"^(?:темно-?\s*|світло-?\s*|яскраво-?\s*|ніжно-?\s*|насичено-?\s*|глибоко-?\s*)?"
    r"(?:коричнев|чорн|біл|бежев|син|зелен|рожев|червон|сірий|леопард|молочн|кремов|"
    r"шоколад|бордо|хакі|оливков|пудров|м.ятн|лавандов|бузков|жовт|оранжев|фіолетов|"
    r"срібн|золот|графіт|пісочн)",
    re.IGNORECASE,
)
_BARE_LETTER_ONLY_RE = re.compile(
    rf"^📏\s*({_SIZE_LETTER})\s*$",
    re.IGNORECASE,
)
_BARE_LETTER_LIST_RE = re.compile(
    rf"^{_SIZE_LETTER}(?:\s+{_SIZE_LETTER})+$",
    re.IGNORECASE,
)
_COLOR_ALL_SIZES_PRICE_RE = re.compile(
    rf"^(?P<color>[а-яіїєґ'’\s]+?)\s*{_DASH}\s*"
    r"вс[іе]\s+розмір\w*\s+(?:🏷️\s*)?(?P<price>\d[\d\s]*)\s*(?:грн|UAH|₴)?\s*$",
    re.IGNORECASE,
)
_MIN_BARE_PRICE = Decimal("100")
_OLD_PRICE_PAREN_RE = re.compile(r"(?i)\(\s*замість\b[^)]*\)?")
_OLD_PRICE_VALUE_RE = re.compile(
    r"(?i)замість\s*(\d[\d\s]*)|було\s*(\d[\d\s]*)\s*(?:грн|UAH|₴)?|"
    # «₴17,400.00 🏷️7950» — старий формат каналу DropGoods: стара ціна з
    # «₴»-префіксом (кома-тисячні, крапка-десяткові) одразу перед новою
    # ціною з «🏷️», без слова «замість»/«було».
    r"₴\s*([\d,]+(?:\.\d+)?)\s*🏷️"
)

def _to_decimal(raw: str) -> Decimal | None:
    cleaned = raw.replace(" ", "")
    if "." in cleaned and "," in cleaned:
        # «15,600.00» — кома тут розділювач тисяч, а не десяткових.
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None

def _extract_price(text: str) -> Decimal | None:
    # «🏷️ 3250 грн (замість 6500 грн)» — стара ціна не має впливати на вибір.
    text = _OLD_PRICE_PAREN_RE.sub("", text)
    matches = list(_PRICE_TAG_RE.finditer(text))
    if matches:
        # На рядках на кшталт «S — 46–48 … — 3150 UAH» беремо останню ціну.
        match = matches[-1]
        raw = next((group for group in match.groups() if group), None)
        price = _to_decimal(raw) if raw else None
        if price is not None:
            return price

    trailing = _TRAILING_PRICE_RE.search(text.strip())
    if trailing:
        price = _to_decimal(trailing.group(1))
        if price is not None:
            # Без валюти беремо лише правдоподібну ціну, не «46» з діапазону розміру.
            if _has_currency_marker(text) or price >= _MIN_BARE_PRICE:
                return price
        return None

    # Рядок узагалі без тире й без валюти — лише число (можливо, зі старою
    # ціною в дужках, яку вже зрізали вище): «7450 ( замість 12300 )».
    bare = text.strip()
    if re.fullmatch(r"\d[\d\s]*", bare):
        price = _to_decimal(bare)
        if price is not None and price >= _MIN_BARE_PRICE:
            return price
    return None

def _extract_old_price(text: str) -> Decimal | None:
    """Стара ціна з явних форматів «замість N» / «було N» — тільки коли в
    тексті названо ОБИДВІ суми, інакше не вигадуємо compare_price."""
    match = _OLD_PRICE_VALUE_RE.search(text)
    if not match:
        return None
    raw = next((group for group in match.groups() if group), None)
    return _to_decimal(raw) if raw else None

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
    match = _STOCK_NOTE_RE.search(text) or _STOCK_NOTE_GENERIC_RE.search(text)
    if match:
        return int(match.group(1))
    if line_signals_in_stock(text):
        return 1
    return 0

def _normalize_size(raw: str) -> str:
    size = raw.strip().upper().replace(",", ".")
    mapped = _CYR_SIZE_MAP.get(size.lower()) or _CYR_SIZE_MAP.get(raw.strip().lower())
    if mapped:
        return mapped
    if size.isdigit() or (size.replace(".", "", 1).isdigit() and size.count(".") <= 1):
        return size
    return size

_COLOR_SIZE_LABEL_SUFFIX_RE = re.compile(
    r"(?i)\s*розмір(?:и|на\s*сітка)\S*(?:\s*та\s*ціни)?\s*:?\s*$"
)
_COLOR_LABEL_PREFIX_RE = re.compile(r"(?i)^колір\S*(?:\s+\S+)?\s*:\s*")

def _clean_color_header(raw: str) -> str:
    text = raw.lstrip("•▫▪◦").strip()
    text = _COLOR_EMOJI_SUFFIX_RE.sub("", text).strip()
    text = re.sub(r"(?i)\s*[—–\-]?\s*під\s*замовлення\s*$", "", text).strip()
    text = re.sub(r"(?i)\s+під\s*замовлення\s*$", "", text).strip()
    # «блакитна Розміри:» / «чорна Розмірна сітка:» — колір і мітка розділу
    # злиті в один рядок; лишаємо тільки назву кольору.
    text = _COLOR_SIZE_LABEL_SUFFIX_RE.sub("", text).strip()
    # «Колір оправи: золотистий» / «Колір: чорний» — лейбл-префікс перед
    # назвою кольору; лишаємо саме назву, а не весь підпис.
    text = _COLOR_LABEL_PREFIX_RE.sub("", text).strip()
    text = text.strip(" -—–")
    return text

_TRAILING_PAREN_RE = re.compile(r"\(([^)]+)\)\s*$")

def _extract_color_header_name(raw: str) -> str:
    """
    «🤎 Espresso (коричневий)» — англійська назва кольору з українським
    перекладом у дужках; emoji-префікс зрізаємо, а якщо в дужках лежить
    справжнє українське слово-колір — довіряємо саме йому, а не англійській
    назві перед ним. «Темно-синій (Navy)» — навпаки, назва вже українська,
    а дужки — лише зайва позначка мовою оригіналу; тоді просто відкидаємо
    дужки, а не замінюємо ними основну назву.
    """
    de_emojified = _COLOR_EMOJI_PREFIX_RE.sub("", raw.strip()).strip()
    cleaned = _clean_color_header(de_emojified.lstrip("•▫▪◦").strip())
    paren_match = _TRAILING_PAREN_RE.search(cleaned)
    if paren_match:
        if _COLOR_HEADER_RE.match(paren_match.group(1).strip()):
            return paren_match.group(1).strip()
        return cleaned[: paren_match.start()].strip()
    return cleaned

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

    old_price = _extract_old_price(stripped)
    return ParsedVariant(
        size=size,
        price=price,
        compare_price=old_price if old_price and old_price > price else None,
        stock_qty=_extract_stock_qty(stripped, is_available=True),
        is_available=True,
        color=color,
        note=stripped,
    )

def normalize_color_label(raw: str) -> str | None:
    """Зрізати emoji/булети; залишити коротку назву кольору."""
    text = _COLOR_EMOJI_PREFIX_RE.sub("", raw.strip()).strip()
    text = text.lstrip("•▫▪◦- ").strip()
    text = _clean_color_header(text)
    if not text or len(text) > 40:
        return None
    lowered = text.lower()
    if "цін" in lowered or "розмір" in lowered or "сітка" in lowered:
        return None
    if "під замовлення" in lowered:
        return None
    if lowered in {"one size", "onesize"}:
        return None
    # «передоплата», «акція», «знижка», «наявність» — статус/маркетингові
    # слова біля ціни, не назва кольору.
    if any(
        marker in lowered
        for marker in ("передоплат", "акці", "знижк", "наявност", "замовленн")
    ):
        return None
    if _SIZE_TOKEN_ONLY_RE.match(text) or re.search(r"\d", text):
        return None
    if "," in text:
        return None
    if len(text.split()) > 3:
        return None
    return text[0].upper() + text[1:] if text else None

def parse_color_price_line(line: str) -> ParsedVariant | None:
    """
    Рядки формату «🖤 Чорна — 🏷️ 5050 грн» → ONE SIZE + color.
    Не плутати з «• 38 — 🏷️ …».
    """
    stripped = line.strip()
    if not stripped or _SIZE_LINE_RE.match(stripped):
        return None
    if _VARIANT_SECTION_RE.match(stripped):
        return None
    price = _extract_price(stripped)
    if price is None:
        return None
    # Ліва частина до тире перед ціною
    split = re.split(rf"\s*{_DASH}\s*", stripped, maxsplit=1)
    if len(split) < 2:
        return None
    left, right = split[0], split[1]
    if not ("🏷️" in right or _extract_price(right)):
        return None
    color = normalize_color_label(left)
    if not color:
        return None
    sold_out = _is_sold_out(stripped)
    return ParsedVariant(
        size="ONE SIZE",
        price=price,
        stock_qty=0 if sold_out else _extract_stock_qty(stripped, is_available=True),
        is_available=not sold_out,
        color=color,
        note=stripped,
    )

def is_color_price_line(line: str) -> bool:
    return parse_color_price_line(line) is not None

def _is_color_header(line: str, next_line: str | None) -> bool:
    from .parser_variant_extras import _CYR_SIZE_PREORDER_PRICE_RE

    # «коричнева 2 штуки» — колір із кількістю в наявності, а не заголовок
    # кольору перед окремим блоком розмірів/цін.
    if _COLOR_STOCK_LINE_RE.match(line.strip()):
        return False

    stripped = _extract_color_header_name(line)
    if not stripped or len(stripped) > 40:
        return False
    lowered = stripped.lower()
    if "розмір" in lowered or "сітка" in lowered or "📏" in stripped:
        return False
    if "," in stripped:
        return False
    # «під замовлення недоступна» — примітка про статус, не колір;
    # «золотиста фурнітура» — деталь/фурнітура в описі, не варіант кольору.
    if "замовленн" in lowered or "недоступ" in lowered or "фурнітур" in lowered:
        return False
    if _SIZE_LINE_RE.match(stripped) or _VARIANT_SECTION_RE.match(stripped):
        return False
    if _extract_price(stripped):
        return False
    if stripped.endswith(":"):
        return False
    # «чорна 3850» — гола ціна без валюти в кінці рядка; це рядок-варіант,
    # не заголовок кольору (_COLOR_HEADER_RE ловить лише префікс слова).
    if _COLOR_HEADER_RE.match(stripped) and not re.search(r"\d{3,6}\s*$", stripped):
        return True
    if next_line and (
        _SIZE_LINE_RE.match(next_line.strip())
        or "🏷️" in next_line
        or _CYR_SIZE_PREORDER_PRICE_RE.match(next_line.strip())
        or _SIZE_LIST_LABEL_RE.match(next_line.strip())
    ):
        if not any(ch.isdigit() for ch in stripped) and len(stripped.split()) <= 3:
            if lowered.endswith(("і", "а", "е", "ові", "еві", "ий")):
                return True
            if _COLOR_HEADER_RE.match(stripped):
                return True
    return False

def _should_wait_for_price_line(line: str, next_line: str | None) -> bool:
    if "🏷️" in line or _extract_price(line):
        return False
    if not next_line:
        return False
    # «🔹 35 (22 см)» без тире й ціни на цьому ж рядку — ціна («🏷️ 8450 грн»)
    # може бути окремим рядком нижче, за порожнім рядком.
    if _SIZE_FOOT_LENGTH_ONLY_RE.match(line):
        return bool("🏷️" in next_line or _extract_price(next_line))
    if not _SIZE_LINE_RE.match(line):
        return False
    if _SIZE_LINE_RE.match(next_line):
        return False
    if "🏷️" in next_line or _extract_price(next_line):
        return True
    return bool(_SIZE_LETTER_EU_RANGE_RE.match(line))

def looks_like_variant_line(
    line: str, *, caption: str, color: str | None = None
) -> bool:
    """
    Єдине джерело правди про те, чи рядок капшена є "варіантним"
    (розмір/колір/ціна) — щоб такий рядок не лишався продубльованим
    текстом у `description`. Використовує ті самі перевірки, що й
    `extract_variants`, тож description і variants завжди узгоджені.
    """
    from .parser_variant_extras import try_parse_extra_variant_line

    stripped = line.strip()
    if not stripped:
        return False
    if _VARIANT_SECTION_RE.match(stripped):
        return True
    if is_color_price_line(stripped):
        return True
    if _SIZE_LINE_RE.match(stripped) or _SIZE_MEASUREMENT_RE.match(stripped):
        return True
    if _SIZE_FOOT_LENGTH_ONLY_RE.match(stripped):
        return True
    if _BARE_LETTER_ONLY_RE.match(stripped) or _BARE_LETTER_LIST_RE.match(stripped):
        return True
    if try_parse_extra_variant_line(stripped, caption=caption, color=color):
        return True
    # Гола ціна («під замовлення 🏷️6550», «2 в наявності 🏷️7550») без
    # прив'язки до конкретного розміру — це той самий рядок, який
    # `extract_variants` перетворює на фолбековий ONE SIZE-варіант; не
    # повинен лишатись ще й текстом в описі.
    if _has_currency_marker(stripped) and _extract_price(stripped) is not None:
        return True
    # «7450 ( замість 12300 )» — гола ціна зі старою ціною в дужках, без
    # валютного маркера на цьому конкретному рядку (він міг бути раніше в
    # капшені); «замість»/«було» — достатньо однозначний маркер сам собою.
    if _extract_old_price(stripped) is not None:
        return True
    return False

def extract_variants(caption: str) -> list[ParsedVariant]:
    from .parser_list_formats import extract_list_format_variants
    from .parser_variant_extras import try_parse_extra_variant_line

    list_variants = extract_list_format_variants(caption)
    if list_variants:
        return list_variants

    lines = caption.splitlines()
    variants: list[ParsedVariant] = []
    current_color: str | None = None
    current_availability: bool | None = None
    pending_size_line: str | None = None
    measurement_sizes: list[str] = []
    pending_colors: list[tuple[str, int]] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        if _AVAILABILITY_CONTEXT_RE.match(stripped):
            current_availability = True
            pending_size_line = None
            continue
        if _PREORDER_CONTEXT_RE.match(stripped):
            current_availability = False
            pending_size_line = None
            continue

        if _ALL_COLORS_GENERIC_PRICE_RE.match(stripped):
            pending_size_line = None
            continue

        next_line = _next_nonempty_line(lines, index)
        if _is_color_header(stripped, next_line):
            current_color = _extract_color_header_name(stripped) or None
            pending_size_line = None
            continue

        if _VARIANT_SECTION_RE.match(stripped):
            pending_size_line = None
            continue

        if "розмірна сітка" in stripped.lower():
            pending_size_line = None
            continue

        extras = try_parse_extra_variant_line(
            stripped, caption=caption, color=current_color
        )
        if extras:
            variants.extend(extras)
            # Розмір уже отримав власну ціну тут — прибираємо його з
            # measurement_sizes, інакше наприкінці капшена спрацює
            # запасний механізм і додасть ще один (неправильний) варіант.
            for extra_variant in extras:
                if extra_variant.size in measurement_sizes:
                    measurement_sizes.remove(extra_variant.size)
            pending_size_line = None
            continue

        measurement_match = _SIZE_MEASUREMENT_RE.match(stripped)
        if measurement_match:
            # «XS — ОГ 82–86 см — 🏷️ 2950 грн» — рядок несе власну ціну, тож
            # це вже готовий варіант, а не запис для спільної ціни в кінці
            # капшена (інакше всі розміри отримають ОДНУ й ту саму ціну).
            own_price = _extract_price(stripped)
            if own_price is not None:
                sold_out = _is_sold_out(stripped)
                size = _normalize_size(measurement_match.group(1))
                stock_qty = 0
                if not sold_out:
                    stock_qty = _extract_stock_qty(stripped, is_available=True) or 1
                variants.append(
                    ParsedVariant(
                        size=size,
                        price=own_price,
                        stock_qty=stock_qty,
                        is_available=not sold_out,
                        color=current_color,
                        note=stripped,
                    )
                )
            else:
                measurement_sizes.append(_normalize_size(measurement_match.group(1)))
            pending_size_line = None
            continue

        us_eu_cm_match = _SIZE_US_EU_CM_RE.match(stripped)
        if us_eu_cm_match:
            measurement_sizes.append(_normalize_size(us_eu_cm_match.group("size")))
            pending_size_line = None
            continue

        size_list_match = _SIZE_LIST_LABEL_RE.match(stripped)
        if size_list_match:
            for token in re.split(r"\s*,\s*", size_list_match.group("sizes").strip()):
                token = token.strip()
                if _SIZE_TOKEN_ONLY_RE.match(token):
                    measurement_sizes.append(_normalize_size(token))
            pending_size_line = None
            continue

        color_stock_match = _COLOR_STOCK_LINE_RE.match(stripped)
        if color_stock_match:
            color_name = normalize_color_label(color_stock_match.group("color"))
            if color_name and _COLOR_HEADER_RE.match(color_stock_match.group("color")):
                pending_colors.append((color_name, int(color_stock_match.group("qty"))))
                pending_size_line = None
                continue

        if pending_size_line and ("🏷️" in stripped or _extract_price(stripped)):
            sold_out = _is_sold_out(pending_size_line) or _is_sold_out(stripped)
            price = _extract_price(stripped) or _extract_price(pending_size_line)
            size_match = _SIZE_LINE_RE.match(pending_size_line)
            # «SIZE (X см)» без тире — ціна на іншому рядку, без явного
            # маркера наявності поруч; беремо той самий дефолт «1», що й
            # односрядковий формат («🔹 35 (22 см) — 🏷️ …»), а не залишаємо
            # 0, як для звичного pending-розв'язання нижче.
            is_foot_length = size_match is None and bool(
                _SIZE_FOOT_LENGTH_ONLY_RE.match(pending_size_line)
            )
            if is_foot_length:
                size_match = _SIZE_FOOT_LENGTH_ONLY_RE.match(pending_size_line)
            pending_line = pending_size_line
            pending_size_line = None
            if size_match and price is not None:
                size = _normalize_size(size_match.group(1))
                stock_qty = 0
                if not sold_out:
                    stock_qty = _extract_stock_qty(stripped, is_available=True)
                    if not stock_qty and is_foot_length:
                        stock_qty = 1
                old_price = _extract_old_price(stripped) or _extract_old_price(
                    pending_line or ""
                )
                variants.append(
                    ParsedVariant(
                        size=size,
                        price=price,
                        compare_price=old_price if old_price and old_price > price else None,
                        stock_qty=stock_qty,
                        is_available=not sold_out,
                        color=current_color,
                        note=stripped,
                    )
                )
                if size in measurement_sizes:
                    measurement_sizes.remove(size)
            continue

        if _should_wait_for_price_line(stripped, next_line):
            pending_size_line = stripped
            continue

        letter_only_match = _BARE_LETTER_ONLY_RE.match(stripped)
        if letter_only_match:
            measurement_sizes.append(_normalize_size(letter_only_match.group(1)))
            pending_size_line = None
            continue

        if _BARE_LETTER_LIST_RE.match(stripped):
            for token in stripped.split():
                measurement_sizes.append(_normalize_size(token))
            pending_size_line = None
            continue

        variant = _parse_variant_line(stripped, color=current_color)
        if variant:
            variants.append(variant)
            if variant.size in measurement_sizes:
                measurement_sizes.remove(variant.size)
            pending_size_line = None
            continue

        all_sizes_color = _COLOR_ALL_SIZES_PRICE_RE.match(stripped)
        if all_sizes_color and measurement_sizes:
            price = _to_decimal(all_sizes_color.group("price"))
            color = normalize_color_label(all_sizes_color.group("color"))
            if price is not None:
                for size in measurement_sizes:
                    variants.append(
                        ParsedVariant(
                            size=size,
                            price=price,
                            stock_qty=1 if caption_signals_in_stock(caption) else 0,
                            is_available=True,
                            color=color,
                        )
                    )
                measurement_sizes.clear()
                pending_size_line = None
                continue

        color_price = parse_color_price_line(stripped)
        if color_price:
            variants.append(color_price)
            pending_size_line = None
            continue

        if "🏷️" in stripped or _extract_price(stripped):
            price = _extract_price(stripped)
            if price is not None and measurement_sizes:
                if current_availability is not None:
                    stock_qty = 1 if current_availability else 0
                else:
                    stock_default = 0 if "під замовлення" in caption.lower() else 1
                    stock_qty = (
                        1 if caption_signals_in_stock(caption) else stock_default
                    )
                for size in measurement_sizes:
                    # «М» уже підтверджений «в наявності» в попередньому
                    # блоці цього ж капшена — пізніший загальний список
                    # «під замовлення» не повинен понижувати його до 0.
                    already_in_stock = any(
                        v.size == size and v.color == current_color and v.stock_qty > 0
                        for v in variants
                    )
                    if already_in_stock and stock_qty == 0:
                        continue
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

            if price is not None and pending_colors:
                # «зелена лінза 4 штуки» / «коричнева 2 штуки» — кольори з
                # кількістю на власних рядках, а спільна ціна для обох —
                # рядком нижче («…на два кольори одна ціна 🏷️4550»).
                for color_name, qty in pending_colors:
                    variants.append(
                        ParsedVariant(
                            size="ONE SIZE",
                            price=price,
                            stock_qty=qty,
                            is_available=True,
                            color=color_name,
                        )
                    )
                pending_colors = []
                continue

            if price is not None:
                # «передоплата 🏷️350 UAH» / «акція 🏷️1150 (за дві)» —
                # депозит або ціна за кілька штук, коли базова ціна вже
                # знайдена; не підмінюємо нею основний варіант.
                bulk_tier_markers = (
                    "передоплат",
                    "за дві",
                    "за три",
                    "за набір",
                    "акці",
                )
                if variants and any(
                    marker in stripped.lower() for marker in bulk_tier_markers
                ):
                    continue
                # «🏷️4250» / «🏷️4250 замість 6900» — лише ціна (і опційно
                # стара), коли розміри вже зібрані з попередніх рядків
                # («від 39 до 45»). Не плодимо зайвий ONE SIZE.
                price_carrier = re.fullmatch(
                    r"🏷️?\s*\d[\d\s]*(?:\s*(?:UAH|грн|₴))?\s*"
                    r"(?:\(?\s*(?:замість|було)\s*\d[\d\s]*"
                    r"(?:\s*(?:UAH|грн|₴))?\s*\)?)?\s*$",
                    stripped,
                    re.IGNORECASE,
                )
                if price_carrier and variants:
                    old_price = _extract_old_price(stripped)
                    if old_price and old_price > price:
                        variants = [
                            ParsedVariant(
                                size=variant.size,
                                price=variant.price,
                                stock_qty=variant.stock_qty,
                                is_available=variant.is_available,
                                color=variant.color,
                                note=variant.note,
                                compare_price=variant.compare_price or old_price,
                            )
                            for variant in variants
                        ]
                    continue
                size = "ONE SIZE"
                if not variants:
                    size = _wide_size_from_caption(caption) or size
                old_price = _extract_old_price(stripped)
                variants.append(
                    ParsedVariant(
                        size=size,
                        price=price,
                        compare_price=old_price if old_price and old_price > price else None,
                        stock_qty=1 if caption_signals_in_stock(caption) else 0,
                        is_available=True,
                        color=current_color,
                    )
                )

    if measurement_sizes:
        price = _extract_price(caption)
        if price is not None:
            if current_availability is not None:
                stock_qty = 1 if current_availability else 0
            else:
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
            size = _wide_size_from_caption(caption) or "ONE SIZE"
            old_price = _extract_old_price(caption)
            variants.append(
                ParsedVariant(
                    size=size,
                    price=price,
                    compare_price=old_price if old_price and old_price > price else None,
                    stock_qty=1 if caption_signals_in_stock(caption) else 0,
                    is_available=True,
                )
            )

    variants = _apply_named_colors_without_own_price(variants, caption)
    variants = _dedupe_variants_prefer_stock(variants)
    return _backfill_missing_prices(variants)


def _dedupe_variants_prefer_stock(
    variants: list[ParsedVariant],
) -> list[ParsedVariant]:
    """
    Той самий розмір+колір може з’явитись двічі: «1 ХЛ 🏷️1999» (в наявності)
    і пізніше «під замовлення … хл 🏷️1950». Лишаємо варіант з більшим stock.
    """
    best: dict[tuple[str, str], ParsedVariant] = {}
    order: list[tuple[str, str]] = []
    for variant in variants:
        key = (variant.size, (variant.color or "").casefold())
        current = best.get(key)
        if current is None:
            best[key] = variant
            order.append(key)
            continue
        if variant.stock_qty > current.stock_qty:
            best[key] = variant
        elif (
            variant.stock_qty == current.stock_qty
            and variant.is_available
            and not current.is_available
        ):
            best[key] = variant
    return [best[key] for key in order]


def _apply_named_colors_without_own_price(
    variants: list[ParsedVariant], caption: str
) -> list[ParsedVariant]:
    """
    «чорні , рожеві та білі в одну ціну» — розміри/ціни вже розібрані вище
    без кольору (кожен колір коштує однаково); множимо вже знайдені
    безколірні варіанти на кожен названий колір, інакше на сайті колір
    товару неможливо обрати взагалі.
    """
    match = _NAMED_COLORS_SHARED_PRICE_RE.search(caption)
    if not match:
        return variants
    colorless = [v for v in variants if v.color is None]
    if not colorless:
        return variants
    parts = re.split(r"\s*,\s*|\s+(?:та|і)\s+", match.group("colors").strip())
    colors = [normalize_color_label(part) for part in parts if part.strip()]
    colors = [c for c in colors if c]
    if len(colors) < 2:
        return variants
    with_color = [v for v in variants if v.color is not None]
    multiplied = [
        ParsedVariant(
            size=variant.size,
            price=variant.price,
            stock_qty=variant.stock_qty,
            is_available=variant.is_available,
            color=color_name,
            note=variant.note,
            compare_price=variant.compare_price,
        )
        for color_name in colors
        for variant in colorless
    ]
    return with_color + multiplied


def _backfill_missing_prices(
    variants: list[ParsedVariant],
) -> list[ParsedVariant]:
    """«❌ XL — Sold Out» без власної ціни — підставляємо ціну сусіднього
    варіанта того ж товару, щоб не показувати «0 грн» у каталозі."""
    known_prices = [v.price for v in variants if v.price and v.price > 0]
    if not known_prices:
        return variants
    fallback_price = known_prices[-1]
    for variant in variants:
        if not variant.price or variant.price <= 0:
            variant.price = fallback_price
    return variants
