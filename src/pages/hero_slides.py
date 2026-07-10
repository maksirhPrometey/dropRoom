from __future__ import annotations

from django.urls import reverse


def build_hero_slides(hero_slides) -> list[dict[str, str]]:
    catalog_link = reverse("catalog:list")
    slides: list[dict[str, str]] = []

    for slide in hero_slides:
        if not slide.image:
            continue
        slides.append(
            {
                "image_url": slide.image.url,
                "link": catalog_link,
            }
        )

    return slides
