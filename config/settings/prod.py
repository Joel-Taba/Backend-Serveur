"""
Réglages de production : à activer via DJANGO_SETTINGS_MODULE=config.settings.prod.

Toutes les valeurs sensibles doivent être fournies par l'environnement — ce
fichier échoue volontairement fort (via django-environ) si SECRET_KEY ou
ALLOWED_HOSTS ne sont pas définis, plutôt que de démarrer avec des valeurs
par défaut non sûres.
"""
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")  # pas de valeur par défaut : doit être fourni
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # idem

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# --- Durcissement HTTPS / cookies ------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 jours
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Derrière un reverse proxy (nginx, etc.) qui termine le TLS :
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
