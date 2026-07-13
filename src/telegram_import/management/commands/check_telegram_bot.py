from django.conf import settings
from django.core.management.base import BaseCommand

from src.telegram_import.services.telegram_api import TelegramAPIError, get_me


class Command(BaseCommand):
    help = "Перевірити TELEGRAM_BOT_TOKEN і показати дані бота"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(
                self.style.ERROR(
                    "TELEGRAM_BOT_TOKEN не задано. Збережи .env і перезапусти команду."
                )
            )
            return

        try:
            bot = get_me()
        except TelegramAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS("Бот підключений:"))
        self.stdout.write(f"  username: @{bot.get('username', '—')}")
        self.stdout.write(f"  name: {bot.get('first_name', '—')}")
        self.stdout.write(f"  id: {bot.get('id', '—')}")
        self.stdout.write(f"  channel filter: {settings.TELEGRAM_CHANNEL_ID or 'вимкнено (0)'}")
        self.stdout.write(
            f"  import as active: {settings.TELEGRAM_IMPORT_AS_ACTIVE}"
        )
