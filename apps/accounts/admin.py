from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import LoginEvent, User


class UserCreationForm(DjangoUserCreationForm):
    """Le formulaire de Django référence `username` en dur dans son Meta —
    notre User n'a pas ce champ (email uniquement), d'où cette surcharge."""

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "role", "is_active", "is_staff", "date_joined"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["date_joined", "last_login"]
    filter_horizontal = ["groups", "user_permissions"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("full_name",)}),
        (
            "Rôle & permissions",
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2", "role")}),
    )


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "email_attempted", "success", "ip_address"]
    list_filter = ["success"]
    search_fields = ["email_attempted", "ip_address"]
    readonly_fields = [f.name for f in LoginEvent._meta.fields]

    def has_add_permission(self, request):
        return False
