"""Django settings for coachsurmesure.

All environment-specific values come from environment variables (see .env.example); a local .env file is
read with django-dotenv (real environment variables always win). Never commit secrets.
DJANGO_ENV selects "dev" or "prod" and defaults to "prod", so a missing variable fails safe.
"""

import os
import sys
from email.utils import formataddr
from pathlib import Path

import dj_database_url
import dotenv
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from apps.core.observability import build_logging
from apps.core.security import add_pwa_headers, immutable_file_test

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


_dotenv_file = BASE_DIR / ".env"
if _dotenv_file.is_file():  # read_dotenv warns on a missing file; CI and production use real env vars
    dotenv.read_dotenv(str(_dotenv_file))

# Environment flag: "dev" (local work, tests) or "prod" (staging/production). Selects logging profile,
# log directory and the DEBUG default.
APP_ENV = os.environ.get("DJANGO_ENV", "prod").strip().lower()
if APP_ENV not in {"dev", "prod"}:
    raise ImproperlyConfigured(f"DJANGO_ENV must be 'dev' or 'prod', got {APP_ENV!r}")

DEBUG = env_bool("DJANGO_DEBUG", APP_ENV == "dev")
if DEBUG and APP_ENV != "dev":
    raise ImproperlyConfigured("DJANGO_DEBUG=true is only allowed with DJANGO_ENV=dev")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "insecure-dev-only-key"  # noqa: S105 - only used when DEBUG=True
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is off")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.mailer",
    "apps.api",
    "apps.sync",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "apps.core.middleware.RequestLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.security.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: PostgreSQL via DATABASE_URL (see docker-compose.yml for local dev).
if not os.environ.get("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL must be set, e.g. postgres://coach:coach@localhost:5432/coachsurmesure")
DATABASES = {"default": dj_database_url.config(conn_max_age=60, conn_health_checks=True)}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalisation: France-first, English default (product decision 2026-11-17), French available.
LANGUAGE_CODE = "en"
LANGUAGES = [("fr", _("French")), ("en", _("English"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# The SPA build (frontend/dist) is served from the site root by WhiteNoise: /assets/*, /sw.js,
# /manifest.webmanifest, icons. index.html is served by apps.core.views.spa_index for all app routes.
SPA_DIST_DIR = BASE_DIR / "frontend" / "dist"
WHITENOISE_ROOT = SPA_DIST_DIR if SPA_DIST_DIR.is_dir() else None
WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test
WHITENOISE_ADD_HEADERS_FUNCTION = add_pwa_headers
WHITENOISE_MIMETYPES = {".webmanifest": "application/manifest+json"}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# API: session + CSRF auth only (same-origin SPA). No tokens in localStorage, no CORS.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "sync": "120/min",
        "register": "10/hour",
        "verify": "30/hour",
        "resend": "10/hour",
        "login": "60/hour",
        "password_reset": "10/hour",
        "account": "10/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}
SPECTACULAR_SETTINGS = {"TITLE": "Coach sur mesure API", "VERSION": "1", "SERVE_INCLUDE_SCHEMA": False}

# Sessions: the installed app works offline for days, so sessions are long-lived but sliding.
# Data written offline stays in the device outbox until the user is logged in again (never dropped).
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_AGE", str(60 * 60 * 24 * 30)))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Security: strict by default outside DEBUG. Run `manage.py check --deploy` in CI.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False  # enable deliberately once the final domain is fixed

# HSTS preload is hard to undo; it is a conscious decision for backlog 000020, not a default.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Logging: separate dev/prod profiles, rotating files in <DJANGO_LOG_DIR or ./logs>/<dev|prod>/.
# If the directory cannot be created (e.g. read-only filesystem), fall back to console only.
LOG_DIR: Path | None = Path(os.environ.get("DJANGO_LOG_DIR") or BASE_DIR / "logs") / APP_ENV
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    print(f"WARNING: log directory {LOG_DIR} unavailable ({exc}); logging to console only", file=sys.stderr)  # noqa: T201
    LOG_DIR = None
LOGGING = build_logging(APP_ENV, LOG_DIR, os.environ.get("DJANGO_LOG_LEVEL"))


# Email: console in development, SMTP configured via environment elsewhere (no secrets in the repo).
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_TLS", True)
EMAIL_TIMEOUT = int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "10"))  # seconds; Django default is "wait forever"
# Sender of all platform mails: "DJANGO_CONTACT_NAME <DJANGO_CONTACT_MAIL>".
CONTACT_NAME = os.environ.get("DJANGO_CONTACT_NAME", "Coach sur mesure")
CONTACT_MAIL = os.environ.get("DJANGO_CONTACT_MAIL", "noreply@localhost")
DEFAULT_FROM_EMAIL = formataddr((CONTACT_NAME, CONTACT_MAIL))

# Public base URL used in links inside emails. Never derived from the request's Host header.
SITE_URL = os.environ.get("DJANGO_SITE_URL", "").rstrip("/") or (
    "http://localhost:8000" if DEBUG else (f"https://{ALLOWED_HOSTS[0]}" if ALLOWED_HOSTS else "")
)
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24 * 3  # verification links are valid for 3 days

# Login lockout: after this many failed attempts for an email (existing or not), logins for it are
# refused for the lockout period. Counted per email in the cache, so unknown emails behave identically.
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60

PASSWORD_RESET_TIMEOUT = 60 * 60 * 2  # reset links are valid for 2 hours and work once

VERIFICATION_CODE_TTL = 10 * 60  # email codes (password change) are valid for 10 minutes
VERIFICATION_CODE_MAX_ATTEMPTS = 5

# Mail outbox (apps.mailer): mails are queued in the request and sent by `manage.py send_mail_outbox`.
MAILER_SEND_INLINE = env_bool("DJANGO_MAILER_INLINE")  # dev shortcut: send at once, no worker needed
MAILER_COOLDOWN_SECONDS = 60  # no second mail of the same kind to the same address within this time
MAILER_MAX_ATTEMPTS = 5
MAILER_BACKOFF_SECONDS = 60  # 1, 2, 4, 8 minutes between attempts
MAILER_RETENTION_DAYS = 14  # finished outbox rows are deleted after this
