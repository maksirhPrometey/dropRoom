import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger("src.telegram_import")


class TelegramAPIError(Exception):
    pass


@dataclass
class TelegramPhoto:
    file_id: str
    content: bytes
    filename: str


def _api_url(method: str) -> str:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramAPIError("TELEGRAM_BOT_TOKEN не налаштовано")
    return f"https://api.telegram.org/bot{token}/{method}"


def download_photo(file_id: str) -> TelegramPhoto:
    info_response = requests.get(
        _api_url("getFile"),
        params={"file_id": file_id},
        timeout=30,
    )
    info_response.raise_for_status()
    info_data = info_response.json()
    if not info_data.get("ok"):
        raise TelegramAPIError(info_data.get("description", "getFile failed"))

    file_path = info_data["result"]["file_path"]
    download_url = (
        f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
    )
    photo_response = requests.get(download_url, timeout=60)
    photo_response.raise_for_status()

    extension = file_path.rsplit(".", 1)[-1] if "." in file_path else "jpg"
    return TelegramPhoto(
        file_id=file_id,
        content=photo_response.content,
        filename=f"{file_id}.{extension}",
    )


def set_webhook(url: str, secret_token: str) -> dict:
    response = requests.post(
        _api_url("setWebhook"),
        json={
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ["channel_post", "message"],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "setWebhook failed"))
    return data


def delete_webhook() -> dict:
    response = requests.post(_api_url("deleteWebhook"), timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "deleteWebhook failed"))
    return data


def get_webhook_info() -> dict:
    response = requests.get(_api_url("getWebhookInfo"), timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "getWebhookInfo failed"))
    return data.get("result", {})


def get_me() -> dict:
    response = requests.get(_api_url("getMe"), timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "getMe failed"))
    return data.get("result", {})


def get_updates(*, offset: int = 0, timeout: int = 30) -> list[dict]:
    response = requests.get(
        _api_url("getUpdates"),
        params={
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["channel_post", "message"],
        },
        timeout=timeout + 10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "getUpdates failed"))
    return data.get("result", [])
