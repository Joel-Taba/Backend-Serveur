from django.contrib import admin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ["created_at", "path", "ip_address"]
    list_filter = ["created_at"]
    readonly_fields = [f.name for f in Visit._meta.fields]

    def has_add_permission(self, request):
        return False
