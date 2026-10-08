# ARCHITECTURE

الحالة: **بعد المرحلة 1**. الهدف النهائي في `PROJECT-AUDIT.md` §15.

## الطبقات الحالية

```
proxy المنصة (TLS) ──► gunicorn/Django ──► PostgreSQL
                          │
                          ├ /static/ (whitenoise)
                          ├ /media/  (يحجب books/pdfs/)
                          └ Redis (cache)
```

## تطبيقات Django

| التطبيق | المسؤولية |
|---|---|
| `core` | خدمات مشتركة: health، سياق الموقع، validators للملفات، تطبيع العربية (`arabic.py`)، قراءة الإعدادات (`env.py`)، URL converter للـ slugs العربية، خدمة media مع حجب ملفات الكتب |
| `sources` | سجل المصادر (`Source`) |
| `catalog` | الفهرس: Work, Edition, Person, Contribution, Publisher, Series, Subject, WorkTranslation, AccessLink + الصفحات العامة والبحث |
| `library` | مكتبة المستخدم: SavedWork, Rating, ReadingEntry |
| `accounts` | الدخول، التسجيل، الملف الشخصي، حذف الحساب (بلا نماذج) |
| `books` | النموذج القديم (للقراءة فقط في الإدارة). البيانات نُقلت إلى `catalog` و`library` |

## الواجهة

- قوالب Django بلا أطر خارجية: `static/css/maktaba.css` (نظام تصميم بمتغيرات CSS، RTL بخصائص منطقية، فاتح/داكن، mobile-first)
  و`static/js/maktaba.js` (الوضع الداكن، اقتراحات البحث، الحفظ). لا Tailwind CDN ولا GSAP.
- كل صفحة تعمل بدون JavaScript (النماذج عادية؛ JS تحسين فقط).
- الروابط القديمة (`/category/…`، `/categories/`، `/author/<id>/`، `/dashboard/…`) تُحوَّل بـ 301.

## الإعدادات

- `book_project/settings.py`: كل القيم الحساسة من البيئة (`python-decouple`).
  - `DEBUG` افتراضيًا `False`.
  - PostgreSQL عند ضبط `POSTGRES_DB`، وإلا SQLite (للتطوير المحلي فقط).
  - `PROTECTED_MEDIA_PREFIXES`: مسارات media لا تُخدم للعامة.
  - `.env` يُقرأ من `DOTENV_DIR` (مجلد المشروع على الخادم) إن ضُبط.
  - `POSTGRES_PASSWORD_FILE` مدعوم.
- `book_project/settings_test.py`: إعدادات الاختبار.

## قرارات

| القرار | السبب |
|---|---|
| Modular monolith على Django | فريق صغير، نطاق واحد، ولا حاجة لتعقيد microservices |
| PostgreSQL | تزامن، full-text search، `pg_trgm`، `unaccent`، وحجم يصل لملايين السجلات |
| whitenoise للملفات الثابتة | لا يعتمد على إعداد nginx إضافي، مع ضغط وأسماء ملفات مُعرّفة بالمحتوى |
| Django يخدم `/media/` ويحجب `books/pdfs/` | نفس طوبولوجيا النسخة القديمة (حاوي واحد على المنفذ 80) فيعمل النشر دون تغييرات على الخادم. ملفات الكتب لا تُتاح إلا عبر منطق يتحقق من حالة الحقوق (المرحلة 2) |
| كلمة مرور PostgreSQL مولّدة في volume | لا أسرار في المستودع ولا حاجة لتعديل `.env` على الخادم |
| `requirements.txt` مصدر وحيد للاعتماديات | أُزيل Pipfile لأن Docker كان يعيد توليد requirements منه ويتجاوز أي تعديل |
