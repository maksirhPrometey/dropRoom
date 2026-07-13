from django.urls import path

from . import views

app_name = "telegram_import"

urlpatterns = [
    path("webhook/", views.TelegramWebhookView.as_view(), name="webhook"),
]
