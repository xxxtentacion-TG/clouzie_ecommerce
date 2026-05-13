from django.contrib import admin

from .models import AIChatMessage


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "timestamp", "short_message")
    search_fields = ("user__email", "user_message", "ai_reply")
    list_filter = ("timestamp",)
    readonly_fields = ("user", "user_message", "ai_reply", "timestamp")

    def short_message(self, obj):
        return obj.user_message[:80]

# Register your models here.
