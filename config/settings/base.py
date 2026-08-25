"""
Réglages communs à tous les environnements (dev, prod, tests).

Rien d'ici ne doit contenir de secret en dur : tout passe par des variables
d'environnement (voir `.env.example`). Les fichiers `dev.py` et `prod.py`
n'ajustent que ce qui doit réellement différer d'un environnement à l'autre.
"""
from datetime import timedelta
from pathlib import Path

import environ
from django.db.backends.signals import connection_created

# BASE_DIR pointe sur le dossier Backend/ (racine du projet Django)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.library",
    "apps.analytics",
    "apps.contact",
    "apps.tools",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sert les fichiers statiques (CSS/JS de l'admin Django, de l'API
    # browsable) sans serveur dédié (nginx…) — nécessaire dès que DEBUG=False
    # (config.settings.prod), Django ne les sert plus lui-même.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Base de données — SQLite par défaut (suffisant pour un mini-serveur local),
# surchargeable via DATABASE_URL (ex: postgres://user:pass@host:5432/dbname)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}


def _tune_sqlite_connection(sender, connection, **kwargs) -> None:
    """SQLite est en mode journal classique par défaut : une écriture pose
    un verrou exclusif sur tout le fichier, y compris pour les lectures
    (catalogue, tableau de bord…) qui n'ont pourtant rien à voir avec cette
    écriture. Le mode WAL (Write-Ahead Logging) permet aux lectures de
    continuer pendant qu'une écriture est en cours — sans lui, la moindre
    montée en charge concurrente dégraderait les temps de réponse bien avant
    que le CPU ou la RAM ne deviennent limitants. `busy_timeout` fait
    patienter une requête bloquée (au lieu d'échouer immédiatement avec
    « database is locked ») le temps qu'un verrou se libère — utile dans les
    rares cas où deux écritures se chevauchent malgré le WAL.
    Ignoré si la base n'est pas SQLite (ex. DATABASE_URL pointant vers
    PostgreSQL en production multi-établissements) : ces réglages n'ont pas
    de sens ailleurs."""
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")


connection_created.connect(_tune_sqlite_connection)

# ---------------------------------------------------------------------------
# Cache — FileBasedCache plutôt que LocMemCache (le cache par défaut de
# Django) : gunicorn fait tourner plusieurs processus workers indépendants
# (voir Backend/gunicorn.conf.py), chacun avec sa propre mémoire — un cache
# en mémoire ne serait donc PAS partagé entre eux (une donnée mise en cache
# par le worker qui a traité une requête resterait invisible aux deux
# autres). Le cache fichier, lui, est visible par tous les processus, sans
# ajouter de service externe (Redis/Memcached) hors de portée d'un serveur
# unique aux ressources modestes. Utilisé volontairement seulement sur
# quelques vues à la fraîcheur peu critique (tableau de bord, arborescence
# de la bibliothèque) via @cache_page — jamais sur des données sensibles à
# l'utilisateur courant (jamais par défaut sur tout le site).
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / ".cache" / "django"),
        "TIMEOUT": 60,
    }
}

# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# Aucune contrainte de longueur ou de composition sur les mots de passe —
# choix produit délibéré : l'utilisateur saisit ce qu'il veut.
AUTH_PASSWORD_VALIDATORS: list[dict] = []

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques & médias (documents, couvertures générées)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Refusé par défaut : chaque vue publique doit déclarer AllowAny
    # explicitement. C'est le principe de moindre privilège.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "300/minute",
        # Limites dédiées, appliquées explicitement sur les vues sensibles
        # (voir apps.accounts.views) pour freiner le brute-force.
        "login": "10/minute",
        "register": "5/minute",
        "password_reset": "5/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DATETIME_FORMAT": "iso-8601",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    # Le jeton vit en sessionStorage côté navigateur (voir lib/api.ts) : il
    # disparaît déjà à la fermeture de l'onglet, cette durée ne fait que
    # borner une session laissée ouverte.
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS — liste blanche explicite, jamais de wildcard une fois le frontend
# branché. Vide par défaut tant que rien n'est connecté.
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Email (réinitialisation de mot de passe, notifications) — backend console
# par défaut ; surchargé en prod via variables d'environnement SMTP.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@flores-gong-nota.local")
CONTACT_NOTIFICATION_EMAIL = env("CONTACT_NOTIFICATION_EMAIL", default="joeltaba4@gmail.com")

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:3000")

# ---------------------------------------------------------------------------
# Authentification Google (bouton "Continuer avec Google" côté frontend)
# ---------------------------------------------------------------------------
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")

# ---------------------------------------------------------------------------
# Bibliothèque — mêmes formats que ceux gérés par le lecteur du frontend
# (lib/catalog.ts) : garder les deux listes synchronisées si l'un des deux
# projets change.
# ---------------------------------------------------------------------------
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf": "pdf",
    ".epub": "epub",
    ".json": "json",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".mp4": "video",
    ".webm": "video",
    ".ogg": "video",
    ".mov": "video",
}
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=300)
THUMBNAIL_COVER_WIDTH = 480
THUMBNAIL_PAGE_WIDTH = 220

# ---------------------------------------------------------------------------
# Journalisation — les évènements de sécurité (connexions, échecs d'auth)
# sont toujours tracés, y compris en développement.
# ---------------------------------------------------------------------------
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.security": {"handlers": ["console", "security_file"], "level": "INFO", "propagate": False},
        "apps.accounts": {"handlers": ["console", "security_file"], "level": "INFO", "propagate": False},
    },
}
