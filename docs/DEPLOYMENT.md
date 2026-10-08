# DEPLOYMENT

## المكونات

| الخدمة | الصورة | الدور |
|---|---|---|
| `nginx` | nginx:1.27-alpine | المنفذ العام (افتراضيًا 80). يخدم `/media/` ويحجب `/media/books/pdfs/` |
| `web` | تُبنى من `Dockerfile` | Django + gunicorn على 8000 (داخلي). يشغّل `migrate` و`collectstatic` عند البدء. الملفات الثابتة عبر whitenoise |
| `db` | postgres:16-alpine | قاعدة البيانات. البيانات في volume `pgdata` |
| `redis` | redis:7-alpine | cache (و Celery لاحقًا) |

## الإعداد لأول مرة (الانتقال من النسخة القديمة)

> النسخة القديمة كانت تشغّل gunicorn مباشرة على المنفذ 80 وتستخدم `db.sqlite3`.
> الخطوات التالية لا تحذف `db.sqlite3` ولا ملفات `media/`.

1. **نسخة احتياطية** على الخادم قبل أي شيء:
   ```sh
   mkdir -p backups
   cp db.sqlite3 backups/db.sqlite3.$(date +%Y%m%d-%H%M%S)
   tar czf backups/media-$(date +%Y%m%d-%H%M%S).tgz media/
   ```
2. أضف إلى `.env` على الخادم (انظر `.env.example`):
   ```
   DEBUG=False
   POSTGRES_DB=maktaba
   POSTGRES_USER=maktaba
   POSTGRES_PASSWORD=<كلمة مرور قوية>
   ```
   تأكد أن `MAIN_DOMAIN` صحيح (مثل `https://bookmark.deplois.net`).
3. أوقف الحاوية القديمة: `docker compose down` (قبل `git pull`، لأن اسم الخدمة تغيّر).
4. `git pull`
5. شغّل قاعدة البيانات وانقل البيانات:
   ```sh
   docker compose up -d db redis
   docker compose run --rm \
       -v "$PWD/db.sqlite3:/data/db.sqlite3:ro" \
       -v "$PWD/backups:/backups" \
       web sh scripts/migrate_sqlite_to_postgres.sh
   ```
   السكربت يصدّر نسخة JSON إلى `backups/`، ويرفض التحميل إن كانت PostgreSQL تحتوي بيانات.
6. شغّل الكل: `docker compose up -d --build`
7. تحقق: `curl -s http://localhost/healthz/` → `{"status": "ok", "database": true}`

## التحديثات اللاحقة

```sh
git pull
docker compose up -d --build
```

## الاختبارات

```sh
docker compose -f docker-compose.test.yml run --rm --build tests
docker compose -f docker-compose.test.yml down -v
```
تشغّل: `ruff`، `makemigrations --check`، و`pytest` على PostgreSQL حقيقي.

## HTTPS

إن كانت منصة الاستضافة تنهي TLS أمام nginx وتمرر `X-Forwarded-Proto`، فلا حاجة لشيء إضافي.
عند التأكد أن الموقع يعمل بالكامل عبر HTTPS يمكن تفعيل `SECURE_HSTS_SECONDS` في `.env`.
مع `DEBUG=False` تكون الـ cookies من نوع `Secure`، فتسجيل الدخول عبر HTTP العادي لن يعمل (مقصود).

## تنبيه: ملفات مُتتبعة في git

`db.sqlite3` و`media/` ما زالت مُتتبعة في git. **لم تُزل من التتبع عمدًا**:
إزالة ملف من التتبع ثم `git pull` على الخادم **تحذفه من القرص** هناك.
بعد إتمام الانتقال إلى PostgreSQL ونسخ media احتياطيًا، يمكن إزالتها من التتبع بأمان
(`git rm --cached`) ثم إضافتها إلى `.gitignore`. يبقى محتواها في تاريخ git القديم.
