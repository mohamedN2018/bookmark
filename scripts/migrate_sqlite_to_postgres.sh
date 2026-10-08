#!/bin/sh
# نقل البيانات من SQLite القديم إلى PostgreSQL.
#
# تلقائي: deploy/entrypoint.sh يستدعيه بـ --auto عند كل تشغيل؛ لا يفعل شيئًا
#         إلا إذا كانت PostgreSQL فارغة وملف SQLite موجودًا.
# يدوي:
#   docker compose run --rm book_project sh scripts/migrate_sqlite_to_postgres.sh
#
# - لا يعدّل ملف SQLite الأصلي (يعمل على نسخة مؤقتة).
# - يحفظ نسخة JSON في $BACKUP_DIR قبل التحميل.
# - يرفض التحميل إن كانت PostgreSQL تحتوي بيانات.
set -eu

AUTO=0
[ "${1:-}" = "--auto" ] && AUTO=1

SRC=${LEGACY_SQLITE_PATH:-/data/db.sqlite3}
BACKUP_DIR=${BACKUP_DIR:-/backups}

log() { echo "[sqlite->postgres] $*"; }

if [ ! -f "$SRC" ]; then
    [ "$AUTO" = 1 ] && { log "لا يوجد ملف SQLite قديم ($SRC). لا شيء للنقل."; exit 0; }
    echo "لم يُعثر على $SRC" >&2
    exit 1
fi

EXISTING=$(python manage.py shell --no-imports -v 0 -c "from django.contrib.auth.models import User; from books.models import Book; print(User.objects.count() + Book.objects.count())" | tail -n 1)
if [ "$EXISTING" != "0" ]; then
    if [ "$AUTO" = 1 ]; then
        log "PostgreSQL تحتوي بيانات ($EXISTING سجل). لا حاجة للنقل."
        exit 0
    fi
    echo "PostgreSQL يحتوي بيانات بالفعل ($EXISTING سجل). أوقفت العملية دون تغيير." >&2
    exit 2
fi

STAMP=$(date +%Y%m%d-%H%M%S)
WORK=/tmp/sqlite-work-$STAMP.sqlite3
mkdir -p "$BACKUP_DIR"
OUT=$BACKUP_DIR/sqlite-export-$STAMP.json
cp "$SRC" "$WORK"

log "ترقية نسخة SQLite المؤقتة إلى آخر migrations"
DB_ENGINE=sqlite SQLITE_PATH="$WORK" python manage.py migrate --noinput -v 0

log "تصدير البيانات إلى $OUT"
DB_ENGINE=sqlite SQLITE_PATH="$WORK" python manage.py dumpdata \
    --natural-foreign --natural-primary \
    -e contenttypes -e auth.permission -e admin.logentry -e sessions \
    --indent 2 -o "$OUT"
chmod 600 "$OUT"

log "تحميل البيانات في PostgreSQL"
python manage.py loaddata "$OUT"
rm -f "$WORK"
log "تم. النسخة الاحتياطية: $OUT"
