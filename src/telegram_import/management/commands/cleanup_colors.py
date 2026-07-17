"""
Очищення довідника Color після покрокових фіксів парсера кольорів:
- сміттєві записи («One Size», «Колір оправи: золотистий», «під замовлення
  недоступна», емоджі-префікси тощо), які вже ніде не використовуються
  (0 variants) — видаляються без наслідків;
- регістрові дублікати («Коричневий» / «коричневий») — зливаються в один
  запис (variants перепризначаються на переможця);
- усі кольори без нормального hex_code (лишався дефолтний сірий
  «#cccccc») отримують приблизний колір за коренем слова.
"""

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from src.catalog.models import Color
from src.telegram_import.services.importer import (
    _DEFAULT_COLOR_HEX,
    _guess_hex_code,
    is_valid_hex_color,
)
from src.telegram_import.services.parser_variants import (
    _clean_color_header,
    _COLOR_EMOJI_PREFIX_RE,
)

_TRAILING_ANNOTATION_RE = re.compile(r"\s*\([^)]*\)\s*$")
_HAS_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def _is_clean_name(name: str) -> bool:
    return not _HAS_EMOJI_RE.search(name) and "(" not in name


def _normalize_for_grouping(name: str) -> str:
    """
    Той самий колір часто трапляється в різних «обгортках» — «Молочний»
    vs «Молочний 🤍», «Темно-синій» vs «Темно-синій (Navy)». Для пошуку
    дублікатів порівнюємо без емодзі, без дужок-приміток і без регістру,
    а не лише .lower() як раніше.
    """
    text = _COLOR_EMOJI_PREFIX_RE.sub("", name.strip())
    text = _clean_color_header(text)
    text = _TRAILING_ANNOTATION_RE.sub("", text)
    return text.strip().lower()


class Command(BaseCommand):
    help = "Прибрати сміттєві/дубльовані Color-записи, підтягнути реальні hex-коди."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати план без змін у БД.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # --- 1) План: сміття без жодного використання ---
        unused = list(Color.objects.filter(variants__isnull=True))
        unused_ids = {c.pk for c in unused}
        for color in unused:
            self.stdout.write(f"  видаляю (0 використань): {color.name!r}")

        # --- 2) План: дублікати серед того, що лишиться (без урахування
        # регістру, емодзі й дужок-приміток типу «(Navy)») ---
        groups: dict[str, list[Color]] = defaultdict(list)
        for color in Color.objects.exclude(pk__in=unused_ids):
            groups[_normalize_for_grouping(color.name)].append(color)

        merge_plan: list[tuple[Color, list[Color]]] = []
        for colors in groups.values():
            if len(colors) < 2:
                continue
            # Найчистіша назва (без емодзі/дужок) перемагає завжди, навіть
            # якщо в неї менше використань — це стане канонічним записом.
            colors.sort(
                key=lambda c: (not _is_clean_name(c.name), -c.variants.count(), c.pk)
            )
            winner, *losers = colors
            merge_plan.append((winner, losers))
            for loser in losers:
                self.stdout.write(
                    f"  зливаю {loser.name!r} (#{loser.pk}, "
                    f"{loser.variants.count()} variants) → "
                    f"{winner.name!r} (#{winner.pk})"
                )

        merged_loser_ids = {loser.pk for _winner, losers in merge_plan for loser in losers}

        # --- 3) План: hex-код замість дефолтного сірого АБО взагалі
        # невалідного значення («001» — стара пошкоджена дата) ---
        hex_plan: list[tuple[Color, str]] = []
        for color in Color.objects.exclude(pk__in=unused_ids | merged_loser_ids):
            if is_valid_hex_color(color.hex_code) and color.hex_code != _DEFAULT_COLOR_HEX:
                continue
            guessed = _guess_hex_code(color.name)
            if guessed == _DEFAULT_COLOR_HEX and is_valid_hex_color(color.hex_code):
                continue
            hex_plan.append((color, guessed))
            self.stdout.write(f"  hex {color.name!r}: {color.hex_code!r} → {guessed}")

        if not dry_run:
            with transaction.atomic():
                for winner, losers in merge_plan:
                    for loser in losers:
                        loser.variants.update(color=winner)
                        loser.delete()
                Color.objects.filter(pk__in=unused_ids).delete()
                for color, guessed in hex_plan:
                    color.hex_code = guessed
                    color.save(update_fields=["hex_code"])

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово{suffix}: видалено невикористаних {len(unused)}, "
                f"злито груп дублікатів {len(merge_plan)} "
                f"(прибрано {len(merged_loser_ids)} записів), "
                f"оновлено hex {len(hex_plan)}"
            )
        )
