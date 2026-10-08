# DATA MODEL

```
Subject (هرمي) ◄──M2M── Work ──1:N──► Edition ──1:N──► AccessLink ──► Source
                         │  ▲              │
          Contribution ──┘  │              ├──► Publisher, Series
          (AUTHOR/EDITOR/   │              └──► Source (+source_record_id)
           TRANSLATOR)──► Person
                            │
          WorkTranslation: Work(أصل) ──► Work(ترجمة) + Person(مترجم)
```

## الكيانات

| النموذج | المعنى | أهم الحقول |
|---|---|---|
| `Work` | العمل الفكري المجرد | title, subtitle, original_title, normalized_title, content_type (17 نوعًا), original_language, subjects, keywords, difficulty, doi, external_ids, verification_* |
| `Edition` | تجسيد محدد (طبعة/لغة/ناشر) | language, publisher, series, volume, publication_date/year, page_count, isbn10, isbn13, doi, cover, source + source_record_id |
| `Person` | مؤلف/محرر/مترجم | name, native_name, normalized_name, bio, photo, birth/death_year, nationality, orcid, openalex_id, semantic_scholar_id, wikipedia_url, info_source |
| `Contribution` | ربط شخص بعمل أو طبعة | role, position |
| `WorkTranslation` | ترجمة مُتحقق منها | original, translated, language, translator, publisher, year, evidence |
| `AccessLink` | طريقة وصول قانونية | link_type, url / hosted_file, access_status, rights_status, license, source_owner, rights_evidence, is_broken, http_status |
| `Subject` | تصنيف هرمي | name, name_en, parent, sort_order |
| `Source` (`sources`) | مصدر البيانات | source_type, provider_key, has_api, legal_access_policy, allows_rehosting, reliability, health_status |

## قيود تضمن سلامة البيانات

| القيد | لماذا |
|---|---|
| `unique_edition_per_source_record` | استيراد نفس السجل من نفس المصدر مرتين لا ينتج تكرارًا (idempotent) |
| `access_link_has_url_or_file` | لا رابط وصول فارغ |
| `translation_not_self`، `unique_translation_pair` | |
| `contribution_has_target` | كل مساهمة مرتبطة بعمل أو طبعة |
| `unique_person_orcid` | ORCID يعرّف شخصًا واحدًا |
| ISBN-10/13، DOI، ORCID | تحقق من خانة التحقق (checksum) وتطبيع الصيغة |

## لماذا Work/Edition؟

"Clean Code" عمل واحد له طبعة أولى، ثانية، وترجمة عربية. البحث يعيد **العمل** مرة واحدة، وصفحته تعرض
كل الطبعات. `Work.preferred_edition()` يقدّم الطبعة العربية إن وُجدت.

## جودة البيانات (`catalog/quality.py`)

درجة 0-100 تظهر في لوحة الإدارة فقط، مع قائمة بالناقص:
عنوان 10، وصف 10، مؤلف 15، موضوع 10، لغة 5، سنة 5، ناشر 5، معرّف 15، مصدر 10، حالة وصول معروفة 5، تحقق 10.

## الانتقال من النموذج القديم

`catalog/legacy.py` (يُستدعى من migration `0003` ومن الأمر `import_legacy_books`):
- slug العمل = slug الكتاب القديم (الروابط القديمة تبقى).
- `is_free` و`price` **لا** تُنقل كحالة وصول. ملفات PDF القديمة → `AccessLink` بحالة `UNKNOWN`.
- البريد الإلكتروني للمؤلف لا يُنقل.
- النموذج القديم (`books`) باقٍ حتى تنتقل الواجهات وبيانات المستخدمين (المرحلة 3).
