from django.contrib.auth.models import User
from django.db import models


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Підписник"
        verbose_name_plural = "Підписники"

    def __str__(self) -> str:
        return self.email


class DropNotification(models.Model):
    drop = models.ForeignKey(
        "catalog.Drop",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    email = models.EmailField()
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drop_notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("drop", "email")
        ordering = ["-created_at"]
        verbose_name = "Нагадування про дроп"
        verbose_name_plural = "Нагадування про дропи"

    def __str__(self) -> str:
        return f"{self.email} — {self.drop}"
