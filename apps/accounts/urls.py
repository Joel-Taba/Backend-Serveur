from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("google/", views.GoogleAuthView.as_view(), name="google-auth"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/avatar/", views.AvatarUploadView.as_view(), name="me-avatar"),
    path("me/password/", views.PasswordChangeView.as_view(), name="me-password"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("count/", views.RegisteredAccountsCountView.as_view(), name="count"),
    path("registrations/", views.RegistrationHistoryView.as_view(), name="registrations"),
    path("registrations/<int:pk>/", views.RegistrationDetailView.as_view(), name="registration-detail"),
    path("login-events/", views.LoginHistoryView.as_view(), name="login-events"),
]
