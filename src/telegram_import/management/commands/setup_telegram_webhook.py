from django.core.management.base import BaseCommand

from src.telegram_import.services.telegram_api import (
    TelegramAPIError,
    delete_webhook,
    get_webhook_info,
    set_webhook,
)


class Command(BaseCommand):
    help = "Зареєструвати або видалити Telegram webhook для бота"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Видалити webhook",
        )
        parser.add_argument(
            "--info",
            action="store_true",
            help="Показати поточний webhook",
        )

    def handle(self, *args, **options):
        if options["info"]:
            self._show_info()
            return

        if options["delete"]:
            self._delete()
            return

        self._setup()

    def _show_info(self):
        try:
            info = get_webhook_info()
        except TelegramAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS("Поточний webhook:"))
        for key, value in info.items():
            self.stdout.write(f"  {key}: {value}")

    def _delete(self):
        try:
            result = delete_webhook()
        except TelegramAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return
        self.stdout.write(self.style.SUCCESS(result.get("description", "OK")))

    def _setup(self):
        from django.conf import settings

        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN не задано"))
            return
        if not settings.TELEGRAM_WEBHOOK_URL:
            self.stderr.write(self.style.ERROR("TELEGRAM_WEBHOOK_URL не задано"))
            return
        if not settings.TELEGRAM_WEBHOOK_SECRET:
            self.stderr.write(
                self.style.ERROR("TELEGRAM_WEBHOOK_SECRET не задано (обовʼязково)")
            )
            return

        try:
            result = set_webhook(
                settings.TELEGRAM_WEBHOOK_URL,
                settings.TELEGRAM_WEBHOOK_SECRET,
            )
        except TelegramAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS(result.get("description", "Webhook set")))
        self.stdout.write(f"URL: {settings.TELEGRAM_WEBHOOK_URL}")
