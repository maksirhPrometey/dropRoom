import re

_PRICE_RE = re.compile(r"🏷️|грн|₴", re.IGNORECASE)
_STOCK_NOTE_RE = re.compile(
    r"в\s+наявності|наявності\s+один|лише\s+один",
    re.IGNORECASE,
)


def caption_quality_score(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0

    score = min(len(stripped) // 25, 8)
    if _PRICE_RE.search(stripped):
        score += 25
    if re.search(r"[👜👟👕🧥👓🕶️]", stripped):
        score += 5
    if len(stripped) < 45 and not _PRICE_RE.search(stripped):
        score -= 12
    if _STOCK_NOTE_RE.search(stripped) and len(stripped) < 80:
        score -= 25
    return score


def merge_message_captions(captions: list[str]) -> str:
    unique: list[str] = []
    seen: set[str] = set()
    for text in captions:
        cleaned = text.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)

    if not unique:
        return ""

    ranked = sorted(unique, key=caption_quality_score, reverse=True)
    main = ranked[0]
    main_score = caption_quality_score(main)
    notes = [
        item
        for item in ranked[1:]
        if caption_quality_score(item) < main_score - 5
    ]
    if notes:
        return main + "\n\n" + "\n".join(notes)
    return main
