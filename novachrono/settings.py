"""
core/settings.py — NovaChrono settings
"""

import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- NFR-16: HTTPS / secure communication -----------------------------------
# Every deployment-sensitive value is env-driven so the same code can run
# locally (DEBUG on, http) and in production (DEBUG off, https behind the
# OpenShift edge-TLS route).
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-novachrono-dev-key-change-in-production-2026",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

# Never "*" in production: it enables Host-header attacks. Falls back to the
# dev convenience only while DEBUG is on.
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [
        h.strip()
        for h in os.environ.get(
            "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
        ).split(",")
        if h.strip()
    ]

# Behind the OpenShift route the edge terminates TLS and forwards plain HTTP
# to the pod, so Django must trust X-Forwarded-Proto to see the real scheme
# (otherwise request.is_secure() is False and CSRF origin checks fail).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    # Secure cookies are set above; the admin's own session/login pages work
    # fine over https behind the route.
    CSRF_TRUSTED_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "DJANGO_CSRF_TRUSTED_ORIGINS",
            "https://novachrono-ajaymmathewxyz-dev.apps.rm3.7wse.p1.openshiftapps.com",
        ).split(",")
        if o.strip()
    ]

# --- Authentication redirects (FR-4, FR-5) --------------------------------
# Django's @login_required defaults to "/accounts/login/", but this project
# serves the login page at "/login/" (urls.py, name="login"). Without this,
# an anonymous user clicking the wishlist heart got a hard 404 on a route
# that does not exist instead of being sent to log in.
LOGIN_URL = "login"
# Where @login_required sends a user who is ALREADY authenticated but hits a
# protected page.
LOGIN_REDIRECT_URL = "home"
# After signing out, land on the public home page rather than a protected one.
LOGOUT_REDIRECT_URL = "home"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "products",
    "cart",
    "orders",
    "reviews",
    "certificates",
    "analytics",
    "wishlists",
    "notifications",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "novachrono.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.branding",
                "core.context_processors.cart_stats",
            ],
        },
    },
]

WSGI_APPLICATION = "novachrono.wsgi.application"

# Use SQLite for dev; swap to PostgreSQL in production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email — console backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Payment sandbox
PAYMENT_SANDBOX = True
