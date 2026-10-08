#!/bin/sh
# نقل البيانات من SQLite القديم إلى PostgreSQL.
#
# الاستخدام (من جذر المشروع على الخادم):
#   mkdir -p backups
#   docker compose up -d db redis
#   docker compose run --rm \
#       -v "$PWD/db.sqlite3:/data/db.sqlite3:ro" \
#       -v "$PWD/backups:/backups" \
#       web sh scripts/migrate_sqlite_to_postgres.sh
#
# - لا يعدّل db.sqlite3 الأصلي (يُركَّب للقراءة فقط ويُعمل على نسخة).
# - يحفظ نسخة JSON في backups/ قبل أي شيء.
# - يرفض التحميل إن كانت قاعدة PostgreSQL تحتوي بيانات بالفعل.
set -eu

SRC=${SQLITE_SOURCE:-/data/db.sqlite3}
STAMP=$(date +%Y%m%d-%H%M%S)
WORK=/tmp/sqlite-work-$STAMP.sqlite3
OUT=/backups/sqlite-export-$STAMP.json

[ -f "$SRC" ] || { echo "لم يُعثر على $SRC" >&2; exit 1; }
cp "$SRC" "$WORK"

echo ">> ترقية نسخة SQLite المؤقتة إلى آخر migrations"
DB_ENGINE=sqlite SQLITE_PATH="$WORK" python manage.py migrate --noinput

echo ">> تصدير البيانات إلى $OUT"
DB_ENGINE=sqlite SQLITE_PATH="$WORK" python manage.py dumpdata \
    --natural-foreign --natural-primary \
    -e contenttypes -e auth.permission -e admin.logentry -e sessions \
    --indent 2 -o "$OUT"

echo ">> تجهيز PostgreSQL"
python manage.py migrate --noinput

EXISTING=$(python manage.py shell --no-imports -v 0 -c "from django.contrib.auth.models import User; from books.models import Book; print(User.objects.count() + Book.objects.count())" | tail -n 1)
if [ "$EXISTING" != "0" ]; then
    echo "PostgreSQL يحتوي بيانات بالفعل ($EXISTING سجل). أوقفت العملية دون تغيير." >&2
    echo "النسخة المصدّرة محفوظة في $OUT" >&2
    exit 2
fi

echo ">> تحميل البيانات"
python manage.py loaddata "$OUT"
rm -f "$WORK"
echo ">> تم. النسخة الاحتياطية: $OUT"
