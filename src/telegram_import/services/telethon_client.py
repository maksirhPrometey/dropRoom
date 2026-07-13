from django.conf import settings
from telethon import TelegramClient
from telethon.sessions import StringSession


class TelethonConfigError(Exception):
    pass


def get_telethon_client() -> TelegramClient:
    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH
    session_string = settings.TELEGRAM_SESSION_STRING

    if not api_id or not api_hash:
        raise TelethonConfigError(
            "TELEGRAM_API_ID і TELEGRAM_API_HASH обовʼязкові. "
            "Отримай на https://my.telegram.org"
        )
    if not session_string:
        raise TelethonConfigError(
            "TELEGRAM_SESSION_STRING порожній. "
            "Запусти: python3 manage.py telegram_login"
        )

    return TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
    )
