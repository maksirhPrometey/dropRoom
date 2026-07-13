from django.db import models


class TelegramSyncState(models.Model):
    channel_id = models.BigIntegerField(unique=True, verbose_name="ID каналу")
    last_message_id = models.BigIntegerField(
        default=0,
        verbose_name="Останній message_id",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Остання синхронізація",
    )

    class Meta:
        verbose_name = "Стан синхронізації Telegram"
        verbose_name_plural = "Стани синхронізації Telegram"

    def __str__(self) -> str:
        return f"Канал {self.channel_id} · msg {self.last_message_id}"


class TelegramImport(models.Model):
    STATUS_PENDING = "pending"
    STATUS_IMPORTED = "imported"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Очікує"),
        (STATUS_IMPORTED, "Імпортовано"),
        (STATUS_FAILED, "Помилка"),
        (STATUS_SKIPPED, "Пропущено"),
    ]

    channel_id = models.BigIntegerField(verbose_name="ID каналу")
    message_id = models.BigIntegerField(verbose_name="message_id")
    media_group_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="ID медіа-групи",
    )
    raw_caption = models.TextField(blank=True, verbose_name="Текст поста")
    photo_file_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Telegram file_id фото",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Статус",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_imports",
        verbose_name="Товар",
    )
    error = models.TextField(blank=True, verbose_name="Помилка")
    imported_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Імпортовано о",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Імпорт з Telegram"
        verbose_name_plural = "Імпорти з Telegram"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["channel_id", "message_id"],
                name="telegram_import_unique_message",
            ),
        ]
        indexes = [
            models.Index(fields=["channel_id", "media_group_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"TG {self.channel_id}/{self.message_id} · {self.get_status_display()}"
