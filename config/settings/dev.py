"""Réglages de développement local : DEBUG actif, contraintes assouplies."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# En dev, on autorise le frontend Next.js quel que soit son port local.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
