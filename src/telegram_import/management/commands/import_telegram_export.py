from pathlib import Path

from django.core.management.base import BaseCommand

from src.telegram_import.services.export_import import import_telegram_export


class Command(BaseCommand):
    help = (
        "Імпорт старих товарів з експорту Telegram Desktop (result.json + photos/). "
        "Без Telethon і без привʼязки акаунта до сервера."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "export_path",
            type=str,
            help="Шлях до папки експорту (де лежить result.json)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Макс. кількість постів (0 = усі)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише порахувати пости без запису в БД",
        )

    def handle(self, *args, **options):
        export_dir = Path(options["export_path"]).expanduser().resolve()
        if not export_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Папка не існує: {export_dir}"))
            return

        limit = options["limit"] or None

        self.stdout.write(f"Експорт: {export_dir}")
        if not (export_dir / "result.json").is_file():
            self.stdout.write(
                self.style.WARNING(
                    "Очікується result.json у цій папці.\n"
                    "Telegram Desktop → канал → ⋯ → Export chat history → JSON"
                )
            )

        try:
            stats = import_telegram_export(
                export_dir,
                limit=limit,
                dry_run=options["dry_run"],
            )
        except FileNotFoundError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS("Імпорт з експорту завершено"))
        self.stdout.write(f"  Оброблено: {stats.processed}")
        self.stdout.write(f"  Імпортовано: {stats.imported}")
        self.stdout.write(f"  Пропущено: {stats.skipped}")
        self.stdout.write(f"  Помилок: {stats.failed}")

        for error in stats.errors[:10]:
            self.stderr.write(self.style.WARNING(error))
