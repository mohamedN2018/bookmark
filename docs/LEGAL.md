# LEGAL

المبدأ: **نفهرس كل ما يُسمح بفهرسته، نستضيف فقط ما يُسمح باستضافته، ونربط في غير ذلك.**

## حالات الوصول (`AccessStatus`)

`PUBLIC_DOMAIN`، `OPEN_ACCESS`، `CREATIVE_COMMONS`، `AUTHOR_PROVIDED`، `OFFICIAL_FREE`،
`INSTITUTIONAL_ACCESS`، `PREVIEW_ONLY`، `PAID`، `METADATA_ONLY`، `UNKNOWN` (الافتراضي).

## القواعد المطبّقة في الكود (`AccessLink`)

| الخاصية | الشرط |
|---|---|
| `allows_free_access` (زر قراءة/تحميل مجاني) | الحالة من الخمس الأولى **و** `verification_status=VERIFIED` **و** الرابط غير معطل |
| `can_serve_hosted_file` (نخدم الملف من خادمنا) | ما سبق **و** `rights_status=VERIFIED_FREE` **و** يوجد ملف |
| `is_trusted` | الحالة ليست `UNKNOWN` **و** مُتحقق منها |

- `UNKNOWN` لا يُعرض أبدًا كمصدر موثوق ولا يتحول تلقائيًا إلى مجاني.
- لكل رابط: `license`، `source_owner`، `rights_evidence` (لماذا نعتبر الحالة صحيحة).
- `Source.allows_rehosting` افتراضيًا `False`؛ لا يُفعّل إلا بنص صريح في شروط المصدر.
- الملفات تحت `media/books/pdfs/` لا تُخدم مباشرة أبدًا (`PROTECTED_MEDIA_PREFIXES`)؛ الخدمة عبر view يتحقق من `can_serve_hosted_file` (المرحلة 3).

## الكتب التجارية

نحتفظ بالبيانات الوصفية (العنوان، المؤلف، الناشر، ISBN، الطبعة، السنة، الوصف، الموضوعات، اللغة)
مع روابط: الصفحة الرسمية، الشراء، المعاينة إن وُجدت. الحالة `PAID` أو `PREVIEW_ONLY` أو `METADATA_ONLY`.

## البيانات المنقولة من النسخة الأولى

ملفات PDF المرفوعة سابقًا بلا توثيق حقوق → `UNKNOWN`. لا تُتاح للتحميل حتى تتحقق الإدارة وتسجّل الدليل.
