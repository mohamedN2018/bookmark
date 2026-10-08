# PROJECT AUDIT — Bookmark → المكتبة السرية

- تاريخ الفحص: 2026-10-08
- الفرع: `main` — آخر commit: `bb3496e change nav` (11 commit إجمالًا)
- النطاق: كامل المستودع + قاعدة البيانات المحلية `db.sqlite3` + فحص سطحي للموقع المنشور `https://bookmark.deplois.net/`
- طريقة الفحص: قراءة الكود، استعلامات مباشرة على SQLite، `manage.py check`، `check --deploy`، `makemigrations --check`، `manage.py test` (في venv مؤقت خارج المشروع؛ لم يُعدَّل أي ملف في المشروع).
- ملاحظة: ملف `.env` لم يُقرأ عمدًا (أسرار). تم التحقق فقط من أنه غير موجود في تاريخ git.

---

## 1. Current Architecture

مشروع Django أحادي (monolith) بتطبيق واحد:

```
book_project/        إعدادات Django (settings, urls, wsgi, asgi)
books/               التطبيق الوحيد: models, views (973 سطر), forms, admin, urls
  migrations/        0001_initial, 0002_book_author, 0003_useractivity
  templatetags/      فلتر split واحد
  create_authors.py  أمر management موضوع في مكان خاطئ (ليس داخل management/commands)
templates/           20 قالب HTML (~14,400 سطر) + 3 نسخ احتياطية "base copy*.html"
static/              CSS/JS + node_modules (1114 ملف مُتتبع في git)
media/               PDFs وأغلفة مرفوعة (64MB، مُتتبعة في git)
locale/              ملفات .po للعربية والإنجليزية (غير مُفعّلة فعليًا)
Dockerfile, docker-compose.yml
```

- لا توجد طبقة services، لا API، لا background jobs، لا search layer، لا caching.
- كل المنطق داخل function-based views في ملف واحد.
- العرض: Server-rendered Django templates + Tailwind عبر CDN (`cdn.tailwindcss.com`، وهو غير مخصص للإنتاج) + GSAP + Font Awesome عبر CDN.
- النشر: حاوية واحدة تشغّل gunicorn مباشرة على المنفذ 80، بلا reverse proxy، بلا قاعدة بيانات منفصلة.

## 2. Current Stack

| الطبقة | المستخدم فعليًا | مُثبّت لكن غير مستخدم |
|---|---|---|
| Backend | Django 5.2.9, Python 3.11 (Docker) | DRF, drf-yasg, django-allauth, Celery, redis, boto3, django-storages, whitenoise, debug-toolbar |
| DB | SQLite (`db.sqlite3`) | psycopg2-binary |
| Admin | django-jazzmin | — |
| Forms | django-crispy-forms (bootstrap4 pack، والقوالب تستخدم Tailwind) | — |
| Frontend | Tailwind CDN, GSAP 3.11 **و** 3.12 معًا, Font Awesome 6.0 **و** 6.4, Google Fonts (Cairo) | autoprefixer في `static/node_modules` |
| Config | python-decouple | python-dotenv |
| Tests | — | pytest, pytest-django, coverage |
| Server | gunicorn | — |

أدوات التطوير (black, flake8, isort, pytest) موجودة في حزم الإنتاج نفسها. `Dockerfile` يعيد توليد `requirements.txt` من Pipfile أثناء البناء، فيُكتب فوق الملف الموجود.

## 3. Current Database

### Models (`books/models.py`)

| Model | الحقول الرئيسية | ملاحظات |
|---|---|---|
| `Category` | name, slug, features (نص مفصول بفواصل), description | مسطّح، بلا هرمية |
| `Author` | name, bio, avatar, specialization, website, email, is_featured | بلا معرّفات (ORCID/OpenAlex)، بلا normalized_name |
| `Book` | title, slug, author (FK واحد), author_name, description, cover_image, pdf_file, category (FK واحد), published_year, pages, language (نص حر), file_format, price, is_free, is_featured, downloads, views | بلا ISBN/DOI/publisher/edition/source/license/access_status. مؤلف واحد وتصنيف واحد فقط. |
| `Review` | book, user, rating 1–5, comment | unique (book, user) |
| `ReadingHistory` | user, book, last_read, progress, reading_duration_minutes | |
| `Bookmark` | user, book | unique (user, book) |
| `UserActivity` | user, activity_type, details, visited_at | **معرّف داخل `books/views.py:513`** وليس في models.py |

- `on_delete=CASCADE` على `Book.category` (`models.py:76`): حذف تصنيف يحذف كل كتبه.
- لا indexes مخصصة. لا قيود unique على title/ISBN. `slug` يُولد من العنوان دون معالجة التصادم (حفظ كتابين بنفس العنوان → IntegrityError).
- `makemigrations --check`: لا تغييرات معلّقة (Migrations متسقة مع النماذج).

## 4. Current Data (أرقام حقيقية من `db.sqlite3` المحلي)

| الجدول | العدد |
|---|---|
| Books | **2** |
| Authors | **2** |
| Categories | **2** (`programming`, `Organic Chemistry`) |
| Users | **2** (1 staff/superuser) |
| Reviews | **1** (تقييم 4، تعليق من 4 أحرف) |
| Bookmarks | 2 |
| ReadingHistory | 2 |
| UserActivity | 0 |

الكتب:
1. *Advanced Organic Chemistry Part B: Reactions and Synthesis* (Francis A. Carey) — 2007، 1347 صفحة، `is_free=False`، `price=150`، مميز.
2. *Beginning Django E-Commerce* (Jim McGaw) — 2009، 398 صفحة، `is_free=True`. **ملف الـ PDF المرتبط به محذوف من مجلد العمل** (ضمن الملفات `D` في git status) → رابط مكسور.

الموقع المنشور يعرض نفس الكتاب الأول والتصنيفين، ما يعني غالبًا أن الإنتاج يعمل على بيانات مماثلة.

ملفات media غير مرتبطة بأي سجل (orphans): غلاف "انتصار الدم على السيف"، `2_5253971783106694302.pdf`، `Noor-Book.com__البرمجة_بلغة_البايثون_pink_python.pdf`، `Official_ISC2_Guide_to_the_ISSAP_CBK_Second_Edition.pdf`، نسخ مكررة من الأغلفة (`_jUpFJt1`, `_YSWL9rv`)، وصورتان مكررتان للمؤلف.

الأغلفة هي لقطات شاشة من Chrome (`..._Google_Chrome_1_7_2026_...png`) وليست أغلفة رسمية.

## 5. Current Features

| الميزة | الحالة الفعلية |
|---|---|
| قائمة الكتب + فلترة (تصنيف، سعر، لغة) + بحث | يعمل. البحث = `icontains` على 4 حقول، بلا تطبيع عربي ولا ranking |
| صفحة كتاب | تعمل، لكن أزرار "تحميل الكتاب" و"شراء الآن" `href="#"`، وزر "ابدأ القراءة" يفتح قارئًا وهميًا بنص "هذا نموذج لعرض محتوى الكتاب" |
| تقييمات | تعمل. زر "تحميل المزيد" يضيف **تقييمًا وهميًا** مكتوبًا في JS ("مستخدم جديد") |
| Bookmarks | تعمل في `list.html` و`detail.html`. في `category.html` تستدعي `/api/books/<id>/bookmark/` غير الموجود |
| تصنيفات + صفحات تصنيف | تعمل |
| مؤلفون (قائمة، تفاصيل، كتب المؤلف) | تعمل. `popular_authors` view موجود لكن بلا URL والقالب فارغ (0 سطر) |
| تسجيل/دخول/خروج/ملف شخصي | يعمل مع ثغرات (انظر الأمن) |
| لوحة تحكم مستخدم | تعرض "وقت القراءة" محسوبًا من مجموع نسب التقدم كأنها دقائق (رقم مختلق) |
| لوحة تحكم إدارية (كتب، مستخدمين، إعدادات) | جزئية. صفحة الإعدادات تعرض رسائل نجاح ("تم إنشاء النسخة الاحتياطية بنجاح!") **دون تنفيذ أي شيء**. "المساحة المستخدمة" = مجموع عدد الصفحات |
| حذف كتاب من اللوحة | JS يستدعي `/books/delete/<id>/` غير الموجود (المسار الصحيح `/dashboard/books/<id>/delete/`) |
| حذف/تفاصيل/إضافة مستخدم من اللوحة | تستدعي `/dashboard/users/<id>/delete/`، `/api/users/...` غير موجودة |
| بحث فوري في الهيدر | **وهمي بالكامل**: `base.html:1010` "Simulate API call" يعرض نتائج ثابتة ("كتاب إلكتروني متقدم – أحمد محمد") |
| i18n | `LANGUAGES` معرّفة لكن `LocaleMiddleware` غير مفعّل و`LANGUAGE_CODE='en'` بينما الواجهة عربية ثابتة |
| Django admin (jazzmin) | يعمل للنماذج الستة |

## 6. Current Problems

### 6.1 بيانات ومزاعم مزيفة (مخالفة للقاعدة 1 و39)

| الموقع | النص |
|---|---|
| `base.html:7,10,14-16` | "مكتبة الكتب - منصة القراءة الرقمية"، "منصة القراءة الرقمية الأولى في العالم العربي. اكتشف آلاف الكتب" |
| `home.html:198` | "منصة القراءة الرقمية الرائدة" |
| `home.html:211,736,875` | "آلاف الكتب"، "انضم إلى آلاف القراء" |
| `auth/login.html:82-90` | "50K+ قارئ نشط"، "100K+ كتاب متاح"، "500K+ ..." |
| `auth/register.html:263,333` | "تصفح آلاف الكتب مجاناً"، "10,000+ قارئ جديد شهرياً"، شهادة مقتبسة مختلقة |
| `books/list.html:381` | "آلاف الكتب في متناول يدك" |
| `auth/profile.html:61` | "الأولى" |
| `base.html:999-1030` | نتائج بحث ثابتة مختلقة |
| `books/detail.html:687-710` | تقييمات مختلقة عند "تحميل المزيد" |
| `views.py:53,108` | صور مؤلفين كرتونية من dicebear.com عند غياب الصورة |
| `views.py:423-429` | وقت قراءة مُشتق من نسب التقدم |
| `views.py:704-721` | رسائل حفظ/نسخ احتياطي بلا تنفيذ |

### 6.2 أخطاء وظيفية

- **عدادات الصفحة الرئيسية خاطئة**: `home.html` يستخدم `{{ book_count }}` و`{{ user_count }}` غير الموجودين في السياق (يظهر 0 في الإنتاج، تم التحقق من الموقع)، ويعرض `count_book` (عدد الكتب) تحت عنوان "كاتب ومؤلف".
- `book_detail` (`views.py:263`) يعيد `progress` إلى 0 في كل زيارة (GET يغيّر البيانات)، ويمرر `Book.objects.all()` كاملًا للقالب دون استخدام.
- `views`/`downloads` لا تُزاد أبدًا (`increment_views` غير مستدعى).
- `get_statistics` يحتوي ~55 سطرًا من كود ميت بعد `return` (`views.py:589-642`).
- `BookForm` يحدد السنة القصوى 2024 (`forms.py:52`).
- `CustomUserCreationForm` معرّف مرتين في `forms.py`.
- مسار `delete_book` مسجّل مرتين بنفس الاسم (`urls.py:21,25`).
- `create_authors.py` لن يُكتشف كأمر management.
- `/usr/src/app/static/` في `STATICFILES_DIRS` مسار مطلق خاص بالحاوية.
- لا أي اختبار (`Ran 0 tests`).

## 7. Security Issues

مرتبة حسب الخطورة:

| # | الخطورة | المشكلة | الموقع |
|---|---|---|---|
| S1 | **حرجة** | `DEBUG = True` ثابت في الكود، و`docker-compose` يركّب المستودع نفسه في الإنتاج. صفحات الأخطاء ستكشف الإعدادات والمسارات والـ SQL | `settings.py:24` |
| S2 | **حرجة** | **تصعيد صلاحيات**: أي staff يستطيع منح/سحب `is_staff` لأي مستخدم، وتعطيل أي حساب بما فيه superuser، بلا حماية ذاتية | `views.py:853-879` |
| S3 | **عالية** | **Open redirect** بعد الدخول: `redirect(request.GET.get('next'))` بلا `url_has_allowed_host_and_scheme` | `views.py:914` |
| S4 | **عالية** | تغيير كلمة المرور من الملف الشخصي دون كلمة المرور الحالية ودون validators، والبريد يُكتب بلا تحقق | `views.py:940-954` |
| S5 | **عالية** | `db.sqlite3` مُتتبع في git (يحتوي password hashes وجلسة نشطة و admin log) | git |
| S6 | **عالية (قانونية)** | ملفات PDF لكتب تجارية محمية بحقوق نشر مستضافة في `media/` ومُتتبعة في git (انظر §10) | `media/books/pdfs/` |
| S7 | متوسطة | `ALLOWED_HOSTS=["*"]`، `CSRF_TRUSTED_ORIGINS` بلا scheme (غير صالح في Django ≥4)، `CORS_ORIGIN_WHITELIST` بلا corsheaders | `settings.py:28-34` |
| S8 | متوسطة | لا HSTS، لا SSL redirect، cookies غير secure (`check --deploy`: 5 تحذيرات أمنية) | settings |
| S9 | متوسطة | Logout عبر GET (CSRF logout) | `urls.py:13`, `views.py:930` |
| S10 | متوسطة | رفع ملفات بلا تحقق من النوع/الحجم (PDF/صور) | `BookForm` |
| S11 | متوسطة | `get_statistics` يعيد `str(e)` للعميل | `views.py:587` |
| S12 | متوسطة | `{{ monthly_stats\|safe }}` داخل `<script>` (البيانات حاليًا رقمية، لكن النمط خطر؛ يجب `json_script`) | `dashboard/index.html:515` |
| S13 | منخفضة | لا rate limiting على login/register؛ تسجيل يكشف وجود البريد/الاسم (user enumeration) | |
| S14 | منخفضة | Tailwind CDN + سكربتات CDN بلا SRI؛ لا CSP | `base.html` |
| S15 | منخفضة | `migrate` يُنفذ أثناء `docker build`، و`COPY . .` ينسخ `.env` و`db.sqlite3` إلى الصورة (لا `.dockerignore`) | `Dockerfile` |
| S16 | منخفضة | صلاحيات اللوحة عبر `if not is_staff` يدويًا في كل view بدل decorator/permission موحد | `views.py` |

إيجابي: `.env` غير موجود في تاريخ git. CSRF middleware مفعّل. Django ORM مستخدم دون raw SQL (لا SQL injection ظاهر). `sort_by` مقيّد بقائمة بيضاء.

## 8. Performance Issues

- SQLite مع gunicorn متعدد العمال: قفل كتابة، غير مناسب لـ 100K+ سجل أو كتابات متزامنة.
- N+1 في `home` و`popular_authors` (3–4 استعلامات لكل مؤلف)، و`Book.average_rating()` يحمّل كل التقييمات في Python، ويُستدعى لكل كتاب في القوائم.
- `context_processors.categories_context` يحمّل كل التصنيفات في **كل** طلب.
- `dashboard` ينفذ 12 استعلام count في حلقة أشهر (تقريب `30*i` يوم = أشهر خاطئة أحيانًا).
- `icontains` على description = full table scan؛ لا indexes.
- Tailwind CDN يولّد CSS في المتصفح وقت التشغيل (بطيء، غير مخصص للإنتاج). مكتبتا GSAP وFont Awesome محمّلتان بنسختين.
- قوالب ضخمة (حتى 2127 سطرًا) مع CSS/JS inline مكرر.
- لا caching، لا تحسين صور (لقطات PNG كاملة كأغلفة).
- static/media تُخدم عبر Django `static()` فقط لأن DEBUG=True؛ `whitenoise` مُثبت لكن غير مفعّل.

## 9. UX Issues

- الهوية "مكتبة الكتب / Bookmark" وتصميم "متجر كتب" (أسعار بالجنيه، "شراء الآن"، عربة تسوق) يتعارض مع هدف أرشيف علمي.
- أزرار رئيسية لا تعمل (`href="#"`)، قارئ وهمي، بحث وهمي — تجربة مضللة.
- خليط Bootstrap (crispy) وTailwind، وأنماط متعددة لكل صفحة.
- لا حالة "لم نجد ما تبحث عنه" مفيدة.
- لا شفافية مصدر/رخصة/نوع وصول.
- عدد الصفحات/السنة إلزامي حتى لو غير معروف → يدفع لإدخال قيم مختلقة.
- إمكانية الوصول: لا فحص تباين، أيقونات بلا `aria-label`، حركات GSAP كثيفة بلا احترام `prefers-reduced-motion`.

## 10. Legal / Content Issues

ملفات PDF موجودة في المستودع و/أو مجلد media:

| الملف | التقييم |
|---|---|
| `Official_ISC2_Guide_to_the_ISSAP_CBK_Second_Edition.pdf` | كتاب تجاري (ISC2/CRC Press). لا دليل على تصريح بالاستضافة. |
| `978-1-4302-2536-2*.pdf` (Beginning Django E-Commerce, Apress 2009) | كتاب تجاري. مُعلَّم في القاعدة `is_free=True` — تصنيف وصول غير مُتحقق. |
| `2290a52a-...pdf` (Advanced Organic Chemistry, Springer) | كتاب تجاري. |
| `Noor-Book.com__البرمجة_بلغة_البايثون...pdf` | منقول من موقع طرف ثالث؛ حالة الحقوق غير معروفة. |
| `2_5253971783106694302.pdf` | مجهول المصدر (اسم يشبه ملفات Telegram). |

حتى لو لم تكن روابط التحميل ظاهرة في الواجهة، الملفات قابلة للوصول عبر `/media/...` ومحفوظة في تاريخ git. **التوصية**: إيقاف خدمتها فورًا، تحويل السجلات إلى `METADATA_ONLY`، وقرار المالك بشأن حذفها من تاريخ git (عملية مدمّرة تتطلب موافقة صريحة — لن أنفذها تلقائيًا).

## 11. SEO Issues

- عنوان ووصف ثابتان بمزاعم غير صحيحة في `base.html`؛ لا block للوصف لكل صفحة.
- لا canonical، لا structured data (`schema.org/Book`)، لا breadcrumbs، لا sitemap.xml، لا robots.txt.
- URLs المؤلفين بالـ id (`/author/1/`) بدل slug.
- `LANGUAGE_CODE='en'` مع `<html lang="ar">`.
- محتوى يُحمَّل بالـ JS (عدادات تبدأ بـ 0) يظهر لمحركات البحث كـ 0.

## 12. Technical Debt

- 3 نسخ احتياطية للقالب الأساسي (`base copy.html`, `base copy 2.html`, `base copy 3.html`) داخل `templates/`.
- `static/node_modules` (1114 ملف) و`media/` (64MB) و`db.sqlite3` مُتتبعة في git؛ حجم `.git` = 62MB. سطر `# db.sqlite3` معطّل في `.gitignore`.
- 973 سطرًا في views.py واحد، Model معرّف داخل views، imports مكررة، كود ميت.
- اعتماديات غير مستخدمة كثيرة؛ أدوات dev ضمن الإنتاج؛ Pipfile و requirements.txt متزامنان يدويًا.
- لا linting/CI/tests/type hints.
- README فارغ تقريبًا (`# bookmark`).
- لا logging config، لا health endpoint.

## 13. Reusable Components

ما يستحق الإبقاء عليه أو إعادة استخدامه:

- هيكل مشروع Django 5.2 وإعداد decouple للأسرار.
- منطق Bookmark/Review/ReadingHistory (يُعاد تسميته وتوسيعه إلى مكتبة المستخدم).
- Jazzmin admin كبداية للوحة الإدارة.
- إعدادات Tailwind الملونة ودعم dark mode (`darkMode: 'class'`) و RTL في `base.html` — كنقطة انطلاق للـ Design System بعد إعادة بنائه ببناء Tailwind محلي.
- أسماء الحقول العربية (`verbose_name`) في النماذج.
- البيانات الوصفية الحقيقية للكتابين والمؤلفين (تُرحَّل إلى Work/Edition جديد بعد التحقق).
- الاعتماديات الموجودة مسبقًا التي تناسب الخطة: Celery + redis، psycopg2، DRF، whitenoise، pytest-django.

---

## 14. Risks

| الخطر | الأثر | التخفيف |
|---|---|---|
| استضافة ملفات محمية حاليًا | قانوني/حجب النطاق | إيقاف `/media/books/pdfs` فورًا في المرحلة 1؛ METADATA_ONLY |
| الإنتاج على DEBUG=True | تسريب معلومات | Phase 1 hotfix: settings من البيئة |
| ترحيل SQLite → PostgreSQL | فقدان بيانات | `dumpdata` قبل الترحيل، سكربت ترحيل مُختبَر، لا حذف لـ db.sqlite3 |
| إعادة تصميم Book → Work/Edition | كسر الروابط الحالية `/books/<slug>/` | 301 redirects من الـ slugs القديمة |
| مزوّدات خارجية (rate limits، شروط استخدام متغيرة) | حظر/بيانات خاطئة | Source Registry مع سياسة وصول وحدود لكل مزوّد، User-Agent معرّف، caching |
| تضخم النطاق (46 بندًا) | مشروع لا ينتهي | تنفيذ مرحلي بـ commit لكل Phase واختبارات قبل الانتقال |
| SSRF عبر إدخال URLs | اختراق الشبكة الداخلية | validator مركزي يرفض IP خاصة/loopback/link-local بعد DNS resolve |

---

## 15. Recommended Architecture

### المبادئ
Modular monolith على Django (لا microservices في هذه المرحلة)، PostgreSQL كمصدر الحقيقة ومحرك البحث الأول، Celery للعمليات الخلفية، وطبقة search مجرّدة تسمح بإضافة Meilisearch/OpenSearch لاحقًا دون تغيير الـ views.

### التطبيقات (Django apps)

```
apps/
  core/          إعدادات مشتركة، Arabic normalization، URL validator (SSRF)، health, base models
  catalog/       Work, Edition, Contributor(Person/Org), Contribution(role), Publisher,
                 Identifier(ISBN/DOI/OpenAlex/...), Subject/Topic (هرمي), Series,
                 WorkTranslation, WorkRelation (Knowledge Graph edges), Collection
  sources/       Source, Provider registry, SourceProvider interface, AccessLink
                 (url, access_status, license, rights_status, last_checked, health)
  ingestion/     ImportJob, ImportRecord (raw payload + hash), pipeline stages,
                 dedup candidates + merge, LinkCheck
  search/        SearchBackend interface (Postgres FTS + pg_trgm أولًا)، ranking weights
                 قابلة للتعديل، synonyms، autocomplete، SearchLog (مجهول الهوية)
  library/       (المستخدم) SavedItem, ReadingList, Follow(author/topic/keyword), Alert
  contributions/ Suggestion (book/correction/broken link/translation) → Pending Review
  analytics/     تجميع إحصائي بلا بيانات شخصية: zero-result queries، الأكثر بحثًا
  seo/           sitemaps مقسمة، JSON-LD، meta/OG
  dashboard/     لوحة الإدارة (Django admin مخصص + صفحات health/jobs/duplicates)
```

### البنية التحتية

```
nginx (TLS, static/media, rate limit)
  └─ gunicorn (Django)
PostgreSQL 16 (+ unaccent, pg_trgm, GIN indexes, generated tsvector)
Redis (cache + Celery broker)
Celery worker + Celery beat (sync, link check, enrichment, indexing)
```

### Access model
`AccessLink.access_status ∈ {PUBLIC_DOMAIN, OPEN_ACCESS, CREATIVE_COMMONS, AUTHOR_PROVIDED, OFFICIAL_FREE, INSTITUTIONAL_ACCESS, PREVIEW_ONLY, PAID, METADATA_ONLY, UNKNOWN}`، الافتراضي `UNKNOWN`، ولا يُعرض زر "تحميل" إلا لحالة موثّقة تسمح بالتنزيل. الاستضافة الذاتية للملفات معطّلة افتراضيًا ومشروطة بـ `rights_status` موثّق.

### Search
Postgres أولًا: عمود `search_vector` (عربي + إنجليزي) على نص مُطبَّع (أ/إ/آ→ا، ى→ي، ة→ه، حذف التشكيل والتطويل، فصل "ال" في نسخة مساعدة)، + `pg_trgm` لتحمّل الأخطاء والـ autocomplete، + ranking مركّب بأوزان محفوظة في جدول إعدادات. هذا يكفي حتى ~1M سجل metadata مع indexes صحيحة؛ ويُضاف backend خارجي عند الحاجة خلف نفس الواجهة.

---

## 16. Migration Plan

| Phase | المحتوى | ملاحظات أمان البيانات |
|---|---|---|
| **1a Hotfix** | DEBUG/ALLOWED_HOSTS/CSRF من البيئة، إيقاف خدمة PDFs، إصلاح open redirect وتصعيد الصلاحيات، إزالة كل المزاعم المزيفة والبحث/التقييمات الوهمية، إعادة التسمية إلى "المكتبة السرية"، `.dockerignore`، إخراج node_modules/db/media من التتبع (`git rm --cached` فقط — الملفات تبقى على القرص) | لا حذف لأي ملف من القرص |
| 1b Architecture | هيكل `apps/`، settings مقسمة (base/dev/prod)، docker-compose: postgres, redis, worker, beat, nginx، docs/ARCHITECTURE.md | |
| 2 Data Model | نماذج catalog/sources الجديدة بجانب القديمة، data migration من `Book`→`Work`+`Edition`+`AccessLink(METADATA_ONLY)`، ثم إزالة القديمة لاحقًا بـ migration منفصل | `dumpdata` قبل كل شيء؛ لا حذف migrations |
| 3 UI/Design System | Tailwind build محلي، tokens، RTL، dark/light، مكونات أرشيفية | |
| 4 Search | normalization + FTS + trigram + ranking + autocomplete + zero-result | اختبارات عربية |
| 5 Source Registry | `SourceProvider` interface + أول مزوّدين (مثلًا OpenAlex, Open Library) | احترام rate limits وشروط الاستخدام |
| 6 Import Pipeline | Celery، idempotent عبر (source, external_id) + payload hash | |
| 7 Dedup | ISBN/DOI exact + fuzzy (trigram على normalized title + author) + Merge UI | |
| 8 Knowledge Graph | `WorkRelation` typed edges + related/prerequisites | |
| 9 Admin | dashboards: jobs, health, duplicates, broken links, quality score | |
| 10 User Features | saves/lists/follows/alerts/contributions (Pending Review) | |
| 11 SEO | JSON-LD, sitemaps مقسمة، canonical، OG | |
| 12 Security | مراجعة شاملة، rate limiting، CSP، SSRF tests | |
| 13 Performance | indexes، cursor pagination، caching، load test على بيانات اصطناعية **في بيئة اختبار فقط** | |
| 14 Testing | تغطية لكل البنود في البند 40 | |
| 15 Hardening | backups، logging/monitoring، runbook نشر | |

بعد كل Phase: `pytest`، `ruff`/`flake8`، `mypy` (للوحدات الجديدة)، `makemigrations --check`، بناء Docker، ثم commit منفصل.

### قرارات تحتاج موافقة المالك قبل البدء
1. **ملفات PDF المحمية**: إيقاف خدمتها (موصى به فورًا)، وهل تُحذف من القرص و/أو من تاريخ git (إعادة كتابة التاريخ = force push).
2. **قاعدة البيانات**: الانتقال إلى PostgreSQL (موصى به) — يتطلب تعديل بيئة الخادم.
3. **محرك البحث**: PostgreSQL FTS أولًا (موصى به) أم Meilisearch/OpenSearch من البداية.
4. **إخراج `db.sqlite3` و`media/` و`node_modules` من git** (`git rm --cached`، الملفات تبقى محليًا).
5. **ملفات PDF المحذوفة حاليًا من مجلد العمل** (3 ملفات بحالة `D` قبل بدء الفحص) — هل الحذف مقصود؟
