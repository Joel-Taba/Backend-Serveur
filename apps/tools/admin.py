from django.contrib import admin

from .models import EcosystemTool


@admin.register(EcosystemTool)
class EcosystemToolAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "url", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "description"]
