"""إعدادات الاختبار. تستخدم PostgreSQL إن ضُبط POSTGRES_DB، وإلا SQLite."""

import os

os.environ.setdefault("MY_SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")
os.environ["DEBUG"] = "False"

from .settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
SECURE_SSL_REDIRECT = False
