# ARCHITECTURE

الحالة: **بعد المرحلة 1**. الهدف النهائي في `PROJECT-AUDIT.md` §15.

## الطبقات الحالية

```
nginx ──► gunicorn/Django ──► PostgreSQL
  │              │
  └ /media/      └ Redis (cache)
    (يحجب books/pdfs/)
```

## تطبيقات Django

| التطبيق | المسؤولية |
|---|---|
| `core` | خدمات مشتركة: health check، سياق الموقع (الاسم/الشعار)، validators للملفات المرفوعة، URL converter للـ slugs العربية، صفحة الخصوصية، خدمة media في التطوير مع حجب ملفات الكتب |
| `books` | النماذج الحالية (Book, Author, Category, Review, Bookmark, ReadingHistory, UserActivity) والواجهات |

المراحل القادمة تضيف: `catalog` (Work/Edition/Contributor/Subject/AccessLink)، `sources`، `ingestion`، `search`، `library`، `contributions`، `analytics`، `seo`.

## الإعدادات

- `book_project/settings.py`: كل القيم الحساسة من البيئة (`python-decouple`).
  - `DEBUG` افتراضيًا `False`.
  - PostgreSQL عند ضبط `POSTGRES_DB`، وإلا SQLite (للتطوير المحلي فقط).
  - `PROTECTED_MEDIA_PREFIXES`: مسارات media لا تُخدم للعامة.
- `book_project/settings_test.py`: إعدادات الاختبار.

## قرارات

| القرار | السبب |
|---|---|
| Modular monolith على Django | فريق صغير، نطاق واحد، ولا حاجة لتعقيد microservices |
| PostgreSQL | تزامن، full-text search، `pg_trgm`، `unaccent`، وحجم يصل لملايين السجلات |
| whitenoise للملفات الثابتة | لا يعتمد على إعداد nginx إضافي، مع ضغط وأسماء ملفات مُعرّفة بالمحتوى |
| nginx يحجب `/media/books/pdfs/` | ملفات الكتب لا تُتاح إلا عبر منطق يتحقق من حالة الحقوق (المرحلة 2) |
| `requirements.txt` مصدر وحيد للاعتماديات | أُزيل Pipfile لأن Docker كان يعيد توليد requirements منه ويتجاوز أي تعديل |
