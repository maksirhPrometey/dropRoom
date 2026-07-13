"""Текстовий контент hero-слайдів (без прив'язки до конкретного товару)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pages.models import HeroSlideImage

HERO_SLIDE_VARIANTS: list[dict[str, str]] = [
    {
        "eyebrow": "DROP ROOM",
        "title_line1": "СТИЛЬ,",
        "title_accent": "ЩО В ТЕБЕ.",
        "subtitle": "Мульти-брендовий аутлет оригіналу",
    },
    {
        "eyebrow": "OUTLET",
        "title_line1": "ОРИГІНАЛ,",
        "title_accent": "БЕЗ КОМПРОМІСІВ.",
        "subtitle": "Щотижневі дропи та лімітовані позиції",
    },
    {
        "eyebrow": "MULTI-BRAND",
        "title_line1": "ДОСТУПНО.",
        "title_accent": "ВИГІДНО.",
        "subtitle": "Брендові речі за аутлет-цінами",
    },
]

HERO_SLIDE_SHARED: dict[str, str] = {
    "usp_text": "ДОСТУПНО. ВИГІДНО. ОРИГІНАЛЬНО.",
    "feature_1": "Аутлет ціни",
    "feature_2": "До -50%",
    "feature_3": "Лімітовані позиції",
    "cta_text": "До каталогу",
    "link": "/catalog/",
}


def hero_slide_copy_for_index(index: int) -> dict[str, str]:
    variant = HERO_SLIDE_VARIANTS[index % len(HERO_SLIDE_VARIANTS)]
    return {**HERO_SLIDE_SHARED, **variant}


def apply_hero_slide_copy(slide: HeroSlideImage, index: int) -> None:
    copy = hero_slide_copy_for_index(index)
    slide.eyebrow = copy["eyebrow"]
    slide.title_line1 = copy["title_line1"]
    slide.title_accent = copy["title_accent"]
    slide.subtitle = copy["subtitle"]
    slide.usp_text = copy["usp_text"]
    slide.feature_1 = copy["feature_1"]
    slide.feature_2 = copy["feature_2"]
    slide.feature_3 = copy["feature_3"]
    slide.cta_text = copy["cta_text"]
    slide.link = copy["link"]
