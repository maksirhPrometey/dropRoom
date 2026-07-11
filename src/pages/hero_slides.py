from __future__ import annotations

from django.urls import reverse


def _slide_link(raw: str) -> str:
    link = (raw or "").strip()
    if link.startswith(("http://", "https://", "/")):
        return link
    return reverse("catalog:list")


def build_hero_slides(hero_slides) -> list[dict[str, str]]:
    catalog_link = reverse("catalog:list")
    slides: list[dict[str, str]] = []

    for slide in hero_slides:
        if not slide.image:
            continue
        features = [slide.feature_1, slide.feature_2, slide.feature_3]
        features = [feature.strip() for feature in features if feature and feature.strip()]
        has_panel = any(
            [
                slide.eyebrow,
                slide.title_line1,
                slide.title_accent,
                slide.subtitle,
                slide.usp_text,
                features,
                slide.cta_text,
            ]
        )
        slides.append(
            {
                "image_url": slide.image.url,
                "link": _slide_link(slide.link) if slide.link else catalog_link,
                "eyebrow": slide.eyebrow.strip(),
                "title_line1": slide.title_line1.strip(),
                "title_accent": slide.title_accent.strip(),
                "subtitle": slide.subtitle.strip(),
                "usp_text": slide.usp_text.strip(),
                "features": features,
                "cta_text": slide.cta_text.strip() or "Перейти до каталогу",
                "has_panel": has_panel,
            }
        )

    return slides
