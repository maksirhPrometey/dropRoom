from django.conf import settings
from django.core.management.base import BaseCommand

from src.telegram_import.models import TelegramSyncState
from src.telegram_import.services.telethon_client import TelethonConfigError
from src.telegram_import.services.telethon_sync import sync_telegram_channel


class Command(BaseCommand):
    help = (
        "Синхронізація товарів з Telegram-каналу через Telethon "
        "(історія + нові пости). Для cron кожні 15–30 хв."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel-id",
            type=int,
            help="ID каналу (за замовч. TELEGRAM_CHANNEL_ID)",
        )
        parser.add_argument(
            "--channel",
            type=str,
            help="Username каналу @name (за замовч. TELEGRAM_CHANNEL_USERNAME)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Макс. кількість постів за один запуск (0 = без ліміту)",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Повний backfill історії каналу (від старих до нових)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише порахувати пости без імпорту в БД",
        )
        parser.add_argument(
            "--reset-state",
            action="store_true",
            help="Скинути last_message_id перед синхронізацією",
        )

    def handle(self, *args, **options):
        channel_id = options.get("channel_id") or settings.TELEGRAM_CHANNEL_ID or None
        channel_username = options.get("channel") or settings.TELEGRAM_CHANNEL_USERNAME
        limit = options.get("limit") or None

        if not channel_id and not channel_username:
            self.stderr.write(
                self.style.ERROR(
                    "Вкажи TELEGRAM_CHANNEL_ID або TELEGRAM_CHANNEL_USERNAME у .env"
                )
            )
            return

        if options["reset_state"] and channel_id:
            TelegramSyncState.objects.filter(channel_id=channel_id).update(
                last_message_id=0
            )
            self.stdout.write(self.style.WARNING(f"Скинуто стан для каналу {channel_id}"))

        try:
            stats, resolved_channel_id = sync_telegram_channel(
                channel_id=channel_id,
                channel_username=channel_username,
                limit=limit,
                full=options["full"],
                dry_run=options["dry_run"],
            )
        except TelethonConfigError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return
        except Exception as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            raise

        mode = "повний backfill" if options["full"] else "інкрементальний"
        self.stdout.write(self.style.SUCCESS(f"Синхронізація завершена ({mode})"))
        self.stdout.write(f"  Канал ID: {resolved_channel_id}")
        self.stdout.write(f"  Оброблено постів: {stats.processed}")
        self.stdout.write(f"  Імпортовано: {stats.imported}")
        self.stdout.write(f"  Пропущено: {stats.skipped}")
        self.stdout.write(f"  Помилок: {stats.failed}")

        state = TelegramSyncState.objects.filter(channel_id=resolved_channel_id).first()
        if state:
            self.stdout.write(
                f"  last_message_id: {state.last_message_id} · "
                f"last_sync_at: {state.last_sync_at or '—'}"
            )

        for error in stats.errors[:10]:
            self.stderr.write(self.style.WARNING(error))
        if len(stats.errors) > 10:
            self.stderr.write(
                self.style.WARNING(f"... ще {len(stats.errors) - 10} помилок")
            )
