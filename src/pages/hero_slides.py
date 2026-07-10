from __future__ import annotations

from django.urls import reverse
from django.utils.html import strip_tags

DEFAULT_HERO_SLIDES: tuple[dict[str, str], ...] = (
    {
        "static_image": "images/hero/sneakers.jpg",
        "label": "Footwear",
        "link": "/catalog/",
    },
    {
        "static_image": "images/hero/outerwear.jpg",
        "label": "Outerwear",
        "link": "/catalog/",
    },
    {
        "static_image": "images/hero/lifestyle.jpg",
        "label": "New Drop",
        "link": "/catalog/",
    },
    {
        "static_image": "images/hero/accessories.jpg",
        "label": "Accessories",
        "link": "/catalog/",
    },
    {
        "static_image": "images/hero/denim.jpg",
        "label": "Denim",
        "link": "/catalog/",
    },
)


def _card_label(card, latest_drop) -> str:
    if card.label:
        return card.label
    if card.layout == "drop" and latest_drop:
        return f"Drop {latest_drop.number}"
    return strip_tags(card.title or "DropRoom")


def build_hero_slides(hero_cards, latest_drop) -> list[dict[str, str]]:
    slides: list[dict[str, str]] = []

    for card in hero_cards:
        if not card.image:
            continue
        link = card.get_link() or reverse("catalog:list")
        slides.append(
            {
                "image_url": card.image.url,
                "label": _card_label(card, latest_drop),
                "link": link,
            }
        )

    if len(slides) >= 2:
        return slides

    catalog_link = reverse("catalog:list")
    return [
        {
            "static_image": item["static_image"],
            "label": item["label"],
            "link": item.get("link") or catalog_link,
        }
        for item in DEFAULT_HERO_SLIDES
    ]
