import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from src.telegram_import.services.importer import ImportError, import_telegram_message

logger = logging.getLogger("src.telegram_import")


def _extract_message(update: dict) -> dict | None:
    return update.get("channel_post") or update.get("message")


def _extract_photo_file_ids(message: dict) -> list[str]:
    photos = message.get("photo") or []
    if not photos:
        return []
    return [photos[-1]["file_id"]]


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    def post(self, request):
        if not settings.TELEGRAM_BOT_TOKEN:
            return JsonResponse({"error": "Bot not configured"}, status=503)

        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if settings.TELEGRAM_WEBHOOK_SECRET:
            if secret != settings.TELEGRAM_WEBHOOK_SECRET:
                return HttpResponse(status=403)

        try:
            update = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message = _extract_message(update)
        if not message:
            return JsonResponse({"status": "ignored"})

        chat = message.get("chat") or {}
        channel_id = chat.get("id")
        message_id = message.get("message_id")
        if channel_id is None or message_id is None:
            return JsonResponse({"status": "ignored"})

        caption = message.get("caption") or message.get("text") or ""
        media_group_id = str(message.get("media_group_id") or "")
        photo_file_ids = _extract_photo_file_ids(message)

        try:
            import_telegram_message(
                channel_id=int(channel_id),
                message_id=int(message_id),
                caption=caption,
                photo_file_ids=photo_file_ids,
                media_group_id=media_group_id,
            )
        except ImportError as exc:
            logger.warning("Імпорт TG %s/%s: %s", channel_id, message_id, exc)
        except Exception:
            logger.exception("Помилка webhook TG %s/%s", channel_id, message_id)

        return JsonResponse({"status": "ok"})

    def get(self, request):
        if settings.DEBUG:
            return JsonResponse(
                {
                    "status": "telegram webhook endpoint",
                    "configured": bool(settings.TELEGRAM_BOT_TOKEN),
                }
            )
        return HttpResponse(status=405)
