import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.telegram_import.services.telethon_client import TelethonConfigError


class Command(BaseCommand):
    help = (
        "Одноразовий логін у Telegram для отримання TELEGRAM_SESSION_STRING. "
        "Потрібен TELEGRAM_API_ID і TELEGRAM_API_HASH з my.telegram.org"
    )

    def handle(self, *args, **options):
        api_id = settings.TELEGRAM_API_ID
        api_hash = settings.TELEGRAM_API_HASH
        if not api_id or not api_hash:
            self.stderr.write(
                self.style.ERROR(
                    "Додай TELEGRAM_API_ID і TELEGRAM_API_HASH у .env "
                    "(https://my.telegram.org)"
                )
            )
            return

        self.stdout.write(
            "Увійди в Telegram-акаунт, який має доступ до каналу вигрузки.\n"
            "Після входу скопіюй session string у .env → TELEGRAM_SESSION_STRING\n"
        )

        try:
            session_string = asyncio.run(self._login(api_id, api_hash))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS("Session string (збережи в .env):"))
        self.stdout.write(session_string)

    async def _login(self, api_id: int, api_hash: str) -> str:
        async with TelegramClient(StringSession(), api_id, api_hash) as client:
            await client.start()
            return client.session.save()
