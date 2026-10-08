# DEPLOYMENT

## Dokploy (نوع Docker Compose): الطريقة المعتمدة

1. في Dokploy: **Create Service → Compose**، المصدر: هذا المستودع، الفرع `main`، الملف `docker-compose.yml`.
2. **Environment** (المطلوب فقط):
   ```
   MY_SECRET_KEY=<سلسلة عشوائية طويلة>
   MAIN_DOMAIN=https://bookmark.deplois.net
   ```
   اختياري: `ALLOWED_HOSTS`، `CSRF_TRUSTED_ORIGINS`، `SECURE_HSTS_SECONDS`، `POSTGRES_PASSWORD` (يُولَّد تلقائيًا إن لم يُضبط).
3. **Domains**: أضف `bookmark.deplois.net` للخدمة **`book_project`** على المنفذ **`8000`** مع HTTPS.
   Dokploy يضيف إعدادات Traefik والشبكة تلقائيًا.
4. **Deploy**. لتفعيل النشر التلقائي استخدم Webhook الخاص بخدمة الـ Compose
   (الرابط يكون بالشكل `.../api/deploy/compose/<token>`).
5. بعد نجاح النشر احذف/أوقف تطبيق Dokploy القديم من نوع Application حتى لا يتعارض على الدومين.

### ما يحدث تلقائيًا عند أول نشر

| الخطوة | التفاصيل |
|---|---|
| كلمة مرور PostgreSQL | تُولَّد عشوائيًا وتُحفظ في volume `secrets` (لا أسرار في المستودع) |
| `migrate` + `collectstatic` | عند كل تشغيل للحاوي |
| نقل البيانات القديمة | إن كانت PostgreSQL فارغة: نسخة JSON إلى volume `backups` ثم تحميل بيانات `db.sqlite3` الموجودة في المستودع. لا يتكرر بعد ذلك |
| ملفات media | volume `media` يُملأ من مجلد `media/` الموجود في الصورة عند أول إنشاء |

### الـ volumes (تبقى بين عمليات النشر)

| Volume | المحتوى |
|---|---|
| `pgdata` | قاعدة البيانات |
| `media` | الأغلفة والصور المرفوعة |
| `backups` | نسخ JSON من عمليات النقل |
| `secrets` | كلمة مرور PostgreSQL |

> Dokploy يعيد استنساخ الكود مع كل نشر، لذا لا تُحفظ أي بيانات في مجلد الكود.

## وضع Dokploy Application (القديم)

الـ `Dockerfile` وحده ما زال يعمل (SQLite من المستودع داخل الصورة + media من الصورة)، فالنشر التلقائي القديم
لا يكسر الموقع قبل الانتقال إلى Compose. لكن في هذا الوضع أي تعديل على البيانات يضيع مع كل نشر (كما كان سابقًا).

## التشغيل المحلي

```sh
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
# http://localhost:8000
```
يحتاج `.env` في جذر المشروع فيه `MY_SECRET_KEY` (انظر `.env.example`).

## التحقق

```sh
curl -s https://bookmark.deplois.net/healthz/   # {"status": "ok", "database": true}
```
وفي سجلات الخدمة `book_project` ابحث عن `[sqlite->postgres]`.

## الاختبارات

```sh
docker compose -f docker-compose.test.yml run --rm --build tests
docker compose -f docker-compose.test.yml down -v
```
تشغّل: `ruff`، `makemigrations --check`، و`pytest` على PostgreSQL حقيقي.

## ما تم اختباره قبل الرفع

- تشغيل محلي كامل عبر compose: النقل التلقائي (13 سجل)، الصفحات، media، حجب PDF، تسجيل دخول حقيقي (CSRF + session).
- الحاوي يعمل كمستخدم غير root (`uid 1000`).
- وضع Application (Dockerfile فقط) يعمل بنفس البيانات.
- إعادة النشر لا تكرر النقل.

## تنبيه: ملفات مُتتبعة في git

`db.sqlite3` و`media/` ما زالت في المستودع لأنها مصدر النقل الأول. بعد التأكد من نجاح الانتقال إلى PostgreSQL
يمكن إزالتها من المستودع؛ محتواها يبقى في تاريخ git.
