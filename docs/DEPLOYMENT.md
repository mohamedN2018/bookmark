# DEPLOYMENT

## المكونات (`docker-compose.yml`)

| الخدمة | الدور |
|---|---|
| `book_project` | Django + gunicorn، منشور على `${HTTP_PORT:-80}:8000` (نفس اسم ومنفذ النسخة القديمة). يخدم `/static/` (whitenoise) و`/media/` (مع حجب `/media/books/pdfs/`) |
| `db` | PostgreSQL 16. البيانات في volume `pgdata` |
| `redis` | cache (و Celery لاحقًا) |
| `secrets` | يعمل مرة عند كل تشغيل: يولّد كلمة مرور PostgreSQL إن لم تكن موجودة ويحفظها في volume `secrets` |

## النشر

```sh
git pull
docker compose up -d --build
```

أو عبر Webhook منصة deplois. لا يحتاج أي خطوة يدوية:

1. **كلمة مرور قاعدة البيانات**: تُولَّد عشوائيًا عند أول تشغيل (أو تؤخذ من `POSTGRES_PASSWORD` إن ضُبطت قبل أول تشغيل).
2. **نقل البيانات القديمة**: عند كل تشغيل يتحقق `deploy/entrypoint.sh`: إن كانت PostgreSQL فارغة و`db.sqlite3` موجودًا في مجلد المشروع،
   يصدّر نسخة JSON إلى `backups/` ثم يحمّلها. بعد ذلك لا يفعل شيئًا. ملف SQLite الأصلي لا يُعدَّل (مركّب للقراءة فقط).
3. **الإعدادات**: يُقرأ `.env` من مجلد المشروع كما في النسخة القديمة. المطلوب فقط `MY_SECRET_KEY` و`MAIN_DOMAIN`.
   `DEBUG` مفروض `False` في الإنتاج.

تم اختبار هذا المسار بمحاكاة كاملة: تشغيل النسخة القديمة (`bb3496e`) ثم `git pull` و`docker compose up -d --build` فقط:
الحاوي القديم استُبدل، البيانات نُقلت (13 سجل)، والنشر الثاني لم يكرر النقل.

## التحقق

```sh
curl -s https://bookmark.deplois.net/healthz/   # {"status": "ok", "database": true}
docker compose logs book_project | grep "sqlite->postgres"
```

## الاسترجاع (rollback)

البيانات القديمة لم تُمس: `db.sqlite3` و`media/` كما هي. للعودة للنسخة السابقة:

```sh
git checkout bb3496e -- . && docker compose up -d --build --remove-orphans
```

## الاختبارات

```sh
docker compose -f docker-compose.test.yml run --rm --build tests
docker compose -f docker-compose.test.yml down -v
```
تشغّل: `ruff`، `makemigrations --check`، و`pytest` على PostgreSQL حقيقي.

## HTTPS

الـ proxy الخاص بالمنصة يُنهي TLS. مع `DEBUG=False` تكون الـ cookies من نوع `Secure`.
عند التأكد أن الموقع يعمل بالكامل عبر HTTPS يمكن تفعيل `SECURE_HSTS_SECONDS` في `.env`.

## تنبيه: ملفات مُتتبعة في git

`db.sqlite3` و`media/` ما زالت مُتتبعة في git. **لم تُزل من التتبع عمدًا**:
إزالة ملف من التتبع ثم `git pull` على الخادم **تحذفه من القرص** هناك.
بعد التأكد من نجاح الانتقال إلى PostgreSQL ونسخ `media/` احتياطيًا، يمكن إزالتها من التتبع بأمان.
