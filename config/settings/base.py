from pathlib import Path

from decouple import config
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_htmx",
    "csp",
]

LOCAL_APPS = [
    "src.catalog",
    "src.accounts",
    "src.orders",
    "src.marketing",
    "src.pages",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "libraries": {
                "grid_tags": "src.pages.templatetags.grid_tags",
            },
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "src.pages.context_processors.site_globals",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

CONTENT_SECURITY_POLICY = {
    "EXCLUDE_URL_PREFIXES": ("/admin/",),
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": [
            "'self'",
            "https://fonts.googleapis.com",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
        ],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
}

UNFOLD = {
    "SITE_TITLE": "DropRoom",
    "SITE_HEADER": "DropRoom — Адмінпанель",
    "SITE_SUBHEADER": "Мульти-брендовий концепт-стор",
    "SITE_SYMBOL": "storefront",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "ENVIRONMENT": "config.settings.unfold_callback.environment_callback",
    "STYLES": [
        lambda request: "/static/admin/droproom-admin.css",
    ],
    "COLORS": {
        "primary": {
            "50": "253 248 242",
            "100": "250 240 230",
            "200": "245 224 205",
            "300": "238 200 165",
            "400": "228 165 115",
            "500": "210 130 70",
            "600": "185 100 45",
            "700": "150 78 35",
            "800": "120 62 30",
            "900": "95 50 25",
            "950": "55 28 14",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Каталог",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Товари",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:catalog_product_changelist"),
                    },
                    {
                        "title": "Дропи",
                        "icon": "rocket_launch",
                        "link": reverse_lazy("admin:catalog_drop_changelist"),
                    },
                    {
                        "title": "Бренди",
                        "icon": "sell",
                        "link": reverse_lazy("admin:catalog_brand_changelist"),
                    },
                    {
                        "title": "Категорії",
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                    },
                    {
                        "title": "Кольори",
                        "icon": "palette",
                        "link": reverse_lazy("admin:catalog_color_changelist"),
                    },
                ],
            },
            {
                "title": "Замовлення",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Замовлення",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                    },
                    {
                        "title": "Кошики",
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_cart_changelist"),
                    },
                    {
                        "title": "Промокоди",
                        "icon": "local_offer",
                        "link": reverse_lazy("admin:orders_promocode_changelist"),
                    },
                ],
            },
            {
                "title": "Клієнти",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Користувачі",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Профілі",
                        "icon": "badge",
                        "link": reverse_lazy("admin:accounts_userprofile_changelist"),
                    },
                    {
                        "title": "Адреси",
                        "icon": "location_on",
                        "link": reverse_lazy("admin:accounts_address_changelist"),
                    },
                    {
                        "title": "Вішліст",
                        "icon": "favorite",
                        "link": reverse_lazy("admin:accounts_wishlistitem_changelist"),
                    },
                ],
            },
            {
                "title": "Маркетинг",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Підписники",
                        "icon": "mail",
                        "link": reverse_lazy(
                            "admin:marketing_newslettersubscriber_changelist"
                        ),
                    },
                    {
                        "title": "Нагадування про дроп",
                        "icon": "notifications",
                        "link": reverse_lazy(
                            "admin:marketing_dropnotification_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "Контент сайту",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Налаштування сайту",
                        "icon": "settings",
                        "link": reverse_lazy("admin:pages_sitesettings_changelist"),
                    },
                    {
                        "title": "Головна",
                        "icon": "home",
                        "link": reverse_lazy("admin:pages_homepage_changelist"),
                    },
                    {
                        "title": "Каталог (тексти)",
                        "icon": "view_list",
                        "link": reverse_lazy("admin:pages_catalogpage_changelist"),
                    },
                    {
                        "title": "Про нас",
                        "icon": "auto_stories",
                        "link": reverse_lazy("admin:pages_storypage_changelist"),
                    },
                    {
                        "title": "Контакти",
                        "icon": "contact_page",
                        "link": reverse_lazy("admin:pages_contactspage_changelist"),
                    },
                    {
                        "title": "Анонси (marquee)",
                        "icon": "campaign",
                        "link": reverse_lazy("admin:pages_utilitybaritem_changelist"),
                    },
                ],
            },
        ],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "src": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
