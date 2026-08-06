from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["created_at", "message_type", "name", "email", "is_read"]
    list_filter = ["message_type", "is_read"]
    search_fields = ["name", "email", "message"]
