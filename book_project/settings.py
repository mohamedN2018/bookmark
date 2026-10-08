"""
Django settings for المكتبة السرية.

كل القيم الحساسة أو الخاصة بالبيئة تأتي من متغيرات البيئة (أو ملف .env محليًا).
انظر .env.example و docs/DEPLOYMENT.md.
"""

import os
from pathlib import Path

from decouple import Csv
from django.utils.translation import gettext_lazy as _

from core.env import EnvConfig

BASE_DIR = Path(__file__).resolve().parent.parent

# متغيرات البيئة غير الفارغة لها الأولوية، ثم ملف .env في DOTENV_DIR
# (في Docker: مجلد الكود مركّبًا للقراءة)، وإلا في مجلد المشروع.
config = EnvConfig(Path(os.environ.get("DOTENV_DIR") or BASE_DIR) / ".env")


def secret(name, default=None):
    """يقرأ NAME أو محتوى الملف في NAME_FILE (مثل Docker secrets)."""
    path = config(f"{name}_FILE", default="")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    if default is None:
        return config(name)
    return config(name, default=default)


SITE_NAME = "المكتبة السرية"
SITE_TAGLINE = "المعرفة التي يصعب الوصول إليها، في مكان واحد."


# =========================
# SECURITY
# =========================
def _fallback_secret_key():
    """مفتاح احتياطي عند غياب MY_SECRET_KEY: يُولَّد مرة ويُحفظ في ملف، حتى لا يتوقف الموقع.
    يُستخدم نفس المفتاح في كل العمليات لأن entrypoint (migrate) يُنشئه قبل gunicorn."""
    import logging

    from django.core.management.utils import get_random_secret_key

    path = Path(config("SECRET_KEY_FALLBACK_FILE", default=str(BASE_DIR / ".secret_key")))
    if not path.is_file():
        path.write_text(get_random_secret_key(), encoding="utf-8")
        path.chmod(0o600)
    logging.getLogger(__name__).warning("MY_SECRET_KEY غير مضبوط؛ يُستخدم مفتاح مولّد محليًا من %s", path)
    return path.read_text(encoding="utf-8").strip()


SECRET_KEY = config("MY_SECRET_KEY", default="") or _fallback_secret_key()
DEBUG = config("DEBUG", default=False, cast=bool)

# يقبل "example.com" أو "https://example.com"
MAIN_DOMAIN = config("MAIN_DOMAIN", default="localhost").strip().rstrip("/")
_MAIN_ORIGIN = MAIN_DOMAIN if "://" in MAIN_DOMAIN else f"https://{MAIN_DOMAIN}"
_MAIN_HOST = _MAIN_ORIGIN.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]

# نطاق الإنتاج الحالي مضمّن دائمًا في القيمة الافتراضية
PRODUCTION_HOST = "bookmark.deplois.net"

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default=f"{_MAIN_HOST},{PRODUCTION_HOST},localhost,127.0.0.1",
    cast=Csv(),
)

# Django >= 4 يتطلب scheme في كل origin
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=f"{_MAIN_ORIGIN},https://{_MAIN_HOST},http://{_MAIN_HOST},https://{PRODUCTION_HOST}",
    cast=Csv(),
)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True

if not DEBUG:
    # TLS يُنهى عند الـ reverse proxy الخاص بمنصة الاستضافة
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # فعّله فقط إن كان الـ proxy أمام التطبيق يمرر X-Forwarded-Proto
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)


# =========================
# APPLICATIONS
# =========================
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party
    "crispy_forms",
    # Local
    "core.apps.CoreConfig",
    "sources.apps.SourcesConfig",
    "catalog.apps.CatalogConfig",
    "books.apps.BooksConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "book_project.urls"

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
                "core.context_processors.site",
                "books.context_processors.categories_context",
            ],
        },
    },
]

WSGI_APPLICATION = "book_project.wsgi.application"


# =========================
# DATABASE
# =========================
# PostgreSQL هو قاعدة البيانات المعتمدة. SQLite متاح فقط للتطوير المحلي
# عبر DB_ENGINE=sqlite (وهو الافتراضي إن لم تُضبط POSTGRES_DB).
DB_ENGINE = config("DB_ENGINE", default="postgres" if config("POSTGRES_DB", default="") else "sqlite")

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB"),
            "USER": config("POSTGRES_USER"),
            "PASSWORD": secret("POSTGRES_PASSWORD"),
            "HOST": config("POSTGRES_HOST", default="db"),
            "PORT": config("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": config("SQLITE_PATH", default=str(BASE_DIR / "db.sqlite3")),
        }
    }


# =========================
# CACHE
# =========================
REDIS_URL = config("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }


# =========================
# AUTH
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"


# =========================
# INTERNATIONALIZATION
# =========================
LANGUAGE_CODE = "ar"
TIME_ZONE = config("TIME_ZONE", default="Africa/Cairo")
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("ar", _("Arabic")),
    ("en", _("English")),
]

LOCALE_PATHS = [BASE_DIR / "locale"]


# =========================
# STATIC & MEDIA
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ملفات الكتب لا تُخدم للعامة إلا بعد التحقق من حالة الحقوق.
# Django يخدم /media/ ويحجب هذه المسارات (core.views.serve_public_media).
PROTECTED_MEDIA_PREFIXES = ("books/pdfs/",)

# محاولات الدخول الفاشلة المسموحة لكل اسم مستخدم خلال النافذة الزمنية
LOGIN_MAX_FAILURES = config("LOGIN_MAX_FAILURES", default=10, cast=int)
LOGIN_FAILURE_WINDOW_SECONDS = config("LOGIN_FAILURE_WINDOW_SECONDS", default=900, cast=int)

# حدود رفع الملفات
MAX_PDF_UPLOAD_MB = config("MAX_PDF_UPLOAD_MB", default=200, cast=int)
MAX_IMAGE_UPLOAD_MB = config("MAX_IMAGE_UPLOAD_MB", default=5, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_TEMPLATE_PACK = "bootstrap4"


# =========================
# LOGGING
# =========================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}


# =========================
# ADMIN (Jazzmin)
# =========================
JAZZMIN_SETTINGS = {
    "site_title": SITE_NAME,
    "site_header": SITE_NAME,
    "site_brand": SITE_NAME,
    "welcome_sign": "لوحة إدارة المكتبة السرية",
    "copyright": SITE_NAME,
}
