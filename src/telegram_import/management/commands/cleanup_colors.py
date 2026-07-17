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

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from src.catalog.models import Color
from src.telegram_import.services.importer import _DEFAULT_COLOR_HEX, _guess_hex_code


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

        # --- 2) План: регістрові дублікати серед того, що лишиться ---
        groups: dict[str, list[Color]] = defaultdict(list)
        for color in Color.objects.exclude(pk__in=unused_ids):
            groups[color.name.strip().lower()].append(color)

        merge_plan: list[tuple[Color, list[Color]]] = []
        for colors in groups.values():
            if len(colors) < 2:
                continue
            colors.sort(key=lambda c: (-c.variants.count(), c.pk))
            winner, *losers = colors
            merge_plan.append((winner, losers))
            for loser in losers:
                self.stdout.write(
                    f"  зливаю {loser.name!r} (#{loser.pk}, "
                    f"{loser.variants.count()} variants) → "
                    f"{winner.name!r} (#{winner.pk})"
                )

        merged_loser_ids = {loser.pk for _winner, losers in merge_plan for loser in losers}

        # --- 3) План: hex-код замість дефолтного сірого ---
        hex_plan: list[tuple[Color, str]] = []
        for color in Color.objects.exclude(pk__in=unused_ids | merged_loser_ids):
            if color.hex_code != _DEFAULT_COLOR_HEX:
                continue
            guessed = _guess_hex_code(color.name)
            if guessed == _DEFAULT_COLOR_HEX:
                continue
            hex_plan.append((color, guessed))
            self.stdout.write(f"  hex {color.name!r}: {_DEFAULT_COLOR_HEX} → {guessed}")

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
