from django.conf import settings
from django.db import models


class AIChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_messages",
    )
    user_message = models.TextField()
    ai_reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.timestamp:%Y-%m-%d %H:%M}"
