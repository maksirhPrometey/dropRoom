from django.apps import AppConfig


class TelegramImportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.telegram_import"
    verbose_name = "Telegram імпорт"
