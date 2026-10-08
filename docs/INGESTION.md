# INGESTION — استيراد الكتب

## الأمر

```sh
python manage.py import_source <oapen|gutenberg|arxiv> [--download] [--set cs] [--days 30] [--limit N] [--language ar] [--all-subjects]
                                                 [--max-total-mb N] [--resume TOKEN]
```

في Dokploy: افتح Terminal للخدمة `book_project` ونفّذ الأمر. أمثلة:

```sh
# كل كتب Gutenberg العلمية (روابط قراءة/تحميل من Gutenberg)
python manage.py import_source gutenberg

# كتب OAPEN العلمية (بيانات + غلاف + رابط PDF مباشر من OAPEN)
python manage.py import_source oapen

# أبحاث arXiv في الحاسب خلال آخر 30 يومًا، مع استضافة ملفات الأبحاث المرخصة CC (حد 5GB)
python manage.py import_source arxiv --set cs --days 30 --download --max-total-mb 5000
# مجموعات أخرى: math, physics, q-bio, stat, eess, econ

# استكمال عملية OAPEN توقفت (التوكن يُطبع في آخر السجل ويُحفظ في ImportJob.cursor)
python manage.py import_source oapen --download --resume 'xoai///col_20.500.12657_6/1200'
```

كل عملية تُسجَّل في الإدارة: **المصادر ← عمليات الاستيراد** (مقروء، جديد، محدّث، مكرر، تخطي، ملفات، أخطاء، السجل).

## المراحل (`sources/pipeline.py`)

| المرحلة | التنفيذ |
|---|---|
| Discover + Fetch | المزوّد: OAI-PMH (OAPEN) أو ملف الفهرس الرسمي (Gutenberg) عبر `core.net.fetch` |
| Parse + Normalize | المزوّد → `NormalizedRecord` (عنوان، مؤلفون، لغة ISO-1، سنة، ناشر، ISBN، DOI، صفحات، رخصة، ملفات) |
| Classify | مطابقة Thema/LoCC مع شجرة الموضوعات (`sources/providers/subjects.py`) |
| Validate | معرّف + عنوان + سنة منطقية |
| Filter | افتراضيًا: الموضوعات العلمية + كل ما هو بالعربية (`--all-subjects` لإلغاء) |
| Deduplicate | (المصدر + معرّف السجل) ← ISBN ← DOI ← (العنوان المطبّع + أول مؤلف) |
| Upsert | Work / Edition / Person / Publisher / Subject / AccessLink. كل سجل في transaction مستقلة |
| Download | فقط إن: المزوّد يسمح + الرخصة `VERIFIED_FREE` + الحجم ≤ `MAX_PDF_UPLOAD_MB` + الإجمالي ≤ الحد + المحتوى يبدأ بـ `%PDF-` + MD5 مطابق |
| Index | البحث يعتمد الحقول المطبّعة المحسوبة عند الحفظ |

**Idempotent:** إعادة التشغيل تُحدّث السجلات الموجودة ولا تكرر شيئًا، ولا تعيد تنزيل ملف موجود.

## الحماية عند الجلب (`core/net.py`)

http/https فقط، نطاقات مسموحة لكل مزوّد، رفض العناوين الداخلية/الخاصة (SSRF) مع إعادة الفحص بعد كل تحويل،
حد للحجم أثناء القراءة، مهلة، User-Agent معرّف، وإعادة محاولة بتأخير متزايد.

## المساحة

OAPEN يحتوي ~44 ألف كتاب (متوسط ~10MB). القيمة الافتراضية لكل عملية `IMPORT_MAX_TOTAL_MB=5000`.
راقب مساحة الخادم قبل رفع الحد. الملفات تُحفظ في volume `media` تحت `books/pdfs/` ولا تُخدم إلا عبر
`/access/<id>/file/` بعد التحقق من الرخصة.
