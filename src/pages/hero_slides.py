from __future__ import annotations

from django.urls import reverse


def build_hero_slides(hero_cards) -> list[dict[str, str]]:
    slides: list[dict[str, str]] = []
    catalog_link = reverse("catalog:list")

    for card in hero_cards:
        if not card.image:
            continue
        slides.append(
            {
                "image_url": card.image.url,
                "label": card.label,
                "cta_text": card.cta_text or "Переглянути",
                "link": card.get_link() or catalog_link,
            }
        )

    return slides
