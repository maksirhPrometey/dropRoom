import time

from django.conf import settings
from django.core.management.base import BaseCommand

from src.telegram_import.services.importer import ImportError, import_telegram_message
from src.telegram_import.services.telegram_api import (
    TelegramAPIError,
    delete_webhook,
    get_updates,
    get_webhook_info,
)


def _extract_photo_file_ids(message: dict) -> list[str]:
    photos = message.get("photo") or []
    if not photos:
        return []
    return [photos[-1]["file_id"]]


def _process_update(update: dict, stdout_write) -> None:
    message = update.get("channel_post") or update.get("message")
    if not message:
        return

    chat = message.get("chat") or {}
    channel_id = chat.get("id")
    message_id = message.get("message_id")
    if channel_id is None or message_id is None:
        return

    caption = message.get("caption") or message.get("text") or ""
    media_group_id = str(message.get("media_group_id") or "")
    photo_file_ids = _extract_photo_file_ids(message)

    try:
        record = import_telegram_message(
            channel_id=int(channel_id),
            message_id=int(message_id),
            caption=caption,
            photo_file_ids=photo_file_ids,
            media_group_id=media_group_id,
        )
    except ImportError as exc:
        stdout_write(f"Імпорт пропущено {channel_id}/{message_id}: {exc}")
        return

    stdout_write(
        f"OK {channel_id}/{message_id} → "
        f"{record.get_status_display()} (product_id={record.product_id})"
    )


class Command(BaseCommand):
    help = (
        "Локальний режим: polling getUpdates замість webhook. "
        "Для dev на localhost без ngrok."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Обробити наявні updates один раз і вийти",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=25,
            help="Long polling timeout (сек)",
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(
                self.style.ERROR(
                    "TELEGRAM_BOT_TOKEN не задано. Збережи .env (Cmd+S) і повтори."
                )
            )
            return

        try:
            webhook = get_webhook_info()
        except TelegramAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        if webhook.get("url"):
            self.stdout.write(
                self.style.WARNING(
                    f"Активний webhook: {webhook['url']}. Вимикаю для polling..."
                )
            )
            try:
                delete_webhook()
            except TelegramAPIError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                return

        self.stdout.write(
            self.style.SUCCESS(
                "Polling запущено. Додай бота адміном каналу і опублікуй пост.\n"
                "Зупинка: Ctrl+C"
            )
        )

        offset = 0
        while True:
            try:
                updates = get_updates(offset=offset, timeout=options["timeout"])
            except TelegramAPIError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                time.sleep(3)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                _process_update(update, self.stdout.write)

            if options["once"]:
                break
