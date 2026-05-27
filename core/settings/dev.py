"""
Development settings.
"""

import os

from dotenv import load_dotenv

from .base import *

load_dotenv(BASE_DIR / ".env")

DEBUG = True

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")

ALLOWED_HOSTS = ["*"]
# ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "noreply@securityguard.local"
)

_resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
if _resend_api_key:
    EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
    ANYMAIL = {"RESEND_API_KEY": _resend_api_key}
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
