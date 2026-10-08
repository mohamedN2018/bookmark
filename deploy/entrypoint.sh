#!/bin/sh
set -e

# إن بدأنا كـ root: أصلح ملكية المجلدات القابلة للكتابة فقط، ثم أعد التشغيل كمستخدم app
if [ "$(id -u)" = "0" ]; then
    mkdir -p /usr/src/app/media /usr/src/app/backups /usr/src/app/staticfiles
    chown -R app:app /usr/src/app/media /usr/src/app/backups /usr/src/app/staticfiles
    exec setpriv --reuid=app --regid=app --init-groups sh "$0" "$@"
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

# أول تشغيل على PostgreSQL: نقل بيانات SQLite القديمة إن وُجدت (لا يفعل شيئًا بعد ذلك)
if [ "${DB_ENGINE:-}" = "postgres" ] && [ -n "${LEGACY_SQLITE_PATH:-}" ]; then
    sh /usr/src/app/scripts/migrate_sqlite_to_postgres.sh --auto \
        || echo "[entrypoint] تحذير: فشل نقل بيانات SQLite. التطبيق سيعمل والملف الأصلي لم يُمس."
fi

# نقل أي كتب من النموذج القديم إلى الفهرس الجديد (لا يفعل شيئًا إن نُقلت سابقًا)
python manage.py import_legacy_books || echo "[entrypoint] تحذير: فشل نقل الكتب القديمة إلى الفهرس."

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
    python manage.py collectstatic --noinput -v 0
fi

exec "$@"
