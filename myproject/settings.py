"""
Django settings for myproject project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------
# SECURITY
# -----------------------------

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-this-in-production-use-env-variable"
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# -----------------------------
# CSRF
# -----------------------------

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://lms-portal-zdl9.onrender.com",
]


# -----------------------------
# APPLICATIONS
# -----------------------------

INSTALLED_APPS = [
    "daphne",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "users",
    "courses",
    "enrollments",
    "resources",
    "attendance",
    "certificates",
    "payments",
    "rest_framework",
    "ai_assistant",
    "quizzes",
    "channels",
    "live_classes",
    "notifications",
    "analytics",
    "assignments",
]


# -----------------------------
# CACHE
# -----------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}


# -----------------------------
# MIDDLEWARE
# -----------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# -----------------------------
# URLS
# -----------------------------

ROOT_URLCONF = "myproject.urls"


# -----------------------------
# TEMPLATES
# -----------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [BASE_DIR / "templates"],

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


# -----------------------------
# WSGI / ASGI
# -----------------------------

WSGI_APPLICATION = "myproject.wsgi.application"
ASGI_APPLICATION = "myproject.asgi.application"


# -----------------------------
# CHANNELS
# -----------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}


# -----------------------------
# DATABASE
# -----------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# -----------------------------
# PASSWORD VALIDATION
# -----------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]


# -----------------------------
# INTERNATIONALIZATION
# -----------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# -----------------------------
# STATIC FILES
# -----------------------------

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# -----------------------------
# MEDIA FILES
# -----------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# -----------------------------
# DEFAULT FIELD
# -----------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------
# CUSTOM USER
# -----------------------------

AUTH_USER_MODEL = "users.CustomUser"


# -----------------------------
# LOGIN / LOGOUT
# -----------------------------

LOGIN_URL = "/users/login/"

LOGIN_REDIRECT_URL = "/users/dashboard/"

LOGOUT_REDIRECT_URL = "/users/login/"


# -----------------------------
# FILE UPLOAD
# -----------------------------

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# -----------------------------
# EMAIL SETTINGS
# -----------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    "naveenvanama6886@gmail.com"
)

EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    "bofdaprzkefynugg"
)

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# -----------------------------
# RAZORPAY
# -----------------------------

RAZOR_KEY_ID = os.environ.get(
    "RAZOR_KEY_ID",
    "rzp_test_SR8h8p09AG8XBk"
)

RAZOR_KEY_SECRET = os.environ.get(
    "RAZOR_KEY_SECRET",
    "15v3FoNY7KZpcoQgaWgO0u1f"
)


# -----------------------------
# GEMINI AI
# -----------------------------

GOOGLE_API_KEY = os.environ.get(
    "GOOGLE_API_KEY",
    "AIzaSyD66ExPUmpGy8z8K8V7RuXFq87Zx2Jvjr8"
)