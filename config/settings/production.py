from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())


def _csrf_trusted_origins() -> list[str]:
    """Build trusted origins from env + ALLOWED_HOSTS (HTTPS on prod)."""
    origins: list[str] = []
    raw = config("CSRF_TRUSTED_ORIGINS", default="")
    if raw:
        origins.extend(s.strip() for s in raw.split(",") if s.strip())

    local_hosts = {"localhost", "127.0.0.1", "web", "0.0.0.0"}
    for host in ALLOWED_HOSTS:
        if host in local_hosts:
            origins.append(f"http://{host}")
            continue
        if host.replace(".", "").isdigit():
            origins.extend((f"http://{host}", f"https://{host}"))
            continue
        origins.append(f"https://{host}")
        if not host.startswith("www."):
            origins.append(f"https://www.{host}")

    return list(dict.fromkeys(origins))


CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# nginx terminates TLS — gunicorn speaks plain HTTP on :8000
# SECURE_SSL_REDIRECT must be False inside Docker; nginx handles the redirect.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = ".droproom.com.ua"
CSRF_COOKIE_DOMAIN = ".droproom.com.ua"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# CSRF_TRUSTED_ORIGINS is built in _csrf_trusted_origins() above.

# WhiteNoise removed — static served by nginx from /app/staticfiles
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "csp.middleware.CSPMiddleware",
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}
