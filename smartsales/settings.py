# smartsales/settings.py
from pathlib import Path
from decouple import config, Csv
import dj_database_url
from datetime import timedelta
import os

# ============================================================
# BASE CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = False  # Producción en Render = False

# Render te dará una URL como:
# https://smartsales365-backend.onrender.com
# temporalmente '*' es válido, pero cámbialo cuando tengas el dominio
ALLOWED_HOSTS = ['*']

# ============================================================
# APPS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_yasg",
    "channels",

    # Apps locales
    "users",
    "sucursales",
    "products",
    "ventas",
    "shipping",
    "cart",
    "notifications",
    "bitacora",
    "tenants",
    "reportes",
    "prediccion"
]

# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "smartsales.urls"

# ============================================================
# TEMPLATES
# ============================================================

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

# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = "smartsales.wsgi.application"
ASGI_APPLICATION = 'smartsales.asgi.application'

# ============================================================
# CHANNELS (SIN REDIS PARA RENDER)
# ============================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ============================================================
# DATABASE (Render usa DATABASE_URL)
# ============================================================

DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT"),
        }
    }

# ============================================================
# AUTH PASSWORD
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# LANGUAGE / TIMEZONE
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC / MEDIA
# ============================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# CUSTOM USER
# ============================================================

AUTH_USER_MODEL = "users.User"

# ============================================================
# REST FRAMEWORK + JWT
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "utils.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ============================================================
# CORS / CSRF
# ============================================================

# ⚠️ IMPORTANTE:
# Cambia estas URLs cuando Render genere tus dominios REALES.

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://smartsales365-front.onrender.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://smartsales365-backend-3axi.onrender.com",
    "https://smartsales365-front.onrender.com",
]

# ============================================================
# SWAGGER
# ============================================================

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

# ============================================================
# STRIPE / ONESIGNAL
# ============================================================

STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
ONESIGNAL_REST_API_KEY = config('ONESIGNAL_REST_API_KEY')
ONESIGNAL_APP_ID = config('ONESIGNAL_APP_ID')
