"""نقل الكتب من النموذج القديم (books.Book) إلى Work/Edition/Person/AccessLink.

قواعد النقل (لا اختراع لأي معلومة):
- slug العمل = slug الكتاب القديم، فتبقى الروابط القديمة صالحة.
- is_free و price لا تُنقل كحالة وصول: لم يُتحقق منها. حالة الوصول = UNKNOWN.
- ملف PDF القديم يصبح AccessLink بحالة UNKNOWN وحقوق UNKNOWN، فلا يُعرض للتحميل
  حتى تتحقق الإدارة من الحقوق يدويًا.
- التصنيف القديم يُطابق مع التصنيف الجديد بالاسم (عربي/إنجليزي)، وإلا يُنشأ موضوع بنفس الاسم.
- المؤلف القديم يصبح Person (الاسم، النبذة، الصورة، الموقع). البريد الإلكتروني لا يُنقل
  لأنه بيانات شخصية لا حاجة لها في صفحة عامة.
- العملية idempotent: الكتاب المنقول سابقًا (له Work.legacy_book) يُتخطى.
"""

from django.utils.text import slugify

from core.arabic import normalize_key

LANGUAGE_MAP = {
    "english": "en",
    "الإنجليزية": "en",
    "الانجليزية": "en",
    "انجليزي": "en",
    "en": "en",
    "arabic": "ar",
    "العربية": "ar",
    "عربي": "ar",
    "ar": "ar",
    "french": "fr",
    "الفرنسية": "fr",
}


def _unique_slug(model, value, max_length=255):
    base = slugify(value, allow_unicode=True)[:max_length] or "item"
    slug, n = base, 2
    while model.objects.filter(slug=slug).exists():
        suffix = f"-{n}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        n += 1
    return slug


def import_legacy_books(apps):
    """ينقل الكتب غير المنقولة بعد ويعيد عددها."""
    imported = 0
    Book = apps.get_model("books", "Book")
    Work = apps.get_model("catalog", "Work")
    Edition = apps.get_model("catalog", "Edition")
    Person = apps.get_model("catalog", "Person")
    Contribution = apps.get_model("catalog", "Contribution")
    Subject = apps.get_model("catalog", "Subject")
    AccessLink = apps.get_model("catalog", "AccessLink")
    Source = apps.get_model("sources", "Source")

    manual = Source.objects.get(slug="manual")
    people = {}

    def person_for_author(author):
        if author.pk in people:
            return people[author.pk]
        person = Person.objects.create(
            name=author.name,
            normalized_name=normalize_key(author.name),
            slug=_unique_slug(Person, author.name),
            bio=author.bio or "",
            photo=author.avatar.name if author.avatar else "",
            website=author.website or "",
            is_featured=author.is_featured,
        )
        people[author.pk] = person
        return person

    def person_for_name(name):
        key = normalize_key(name)
        existing = Person.objects.filter(normalized_name=key).first()
        if existing:
            return existing
        return Person.objects.create(name=name, normalized_name=key, slug=_unique_slug(Person, name))

    def subject_for_category(category):
        key = category.name.strip().lower()
        for subject in Subject.objects.all():
            if key in {subject.name.strip().lower(), subject.name_en.strip().lower()}:
                return subject
        return Subject.objects.create(
            name=category.name,
            name_en="",
            slug=_unique_slug(Subject, category.slug or category.name, 150),
            description=category.description or "",
            normalized_name=normalize_key(category.name),
        )

    for book in Book.objects.select_related("author", "category").order_by("pk"):
        if Work.objects.filter(legacy_book_id=book.pk).exists():
            continue

        slug = book.slug if not Work.objects.filter(slug=book.slug).exists() else _unique_slug(Work, book.title)
        language = LANGUAGE_MAP.get((book.language or "").strip().lower(), "")

        work = Work.objects.create(
            title=book.title,
            normalized_title=normalize_key(book.title),
            slug=slug,
            description=book.description or "",
            content_type="BOOK",
            original_language=language,
            is_featured=book.is_featured,
            view_count=book.views or 0,
            legacy_book_id=book.pk,
        )
        if book.category_id:
            work.subjects.add(subject_for_category(book.category))

        if book.author_id:
            person = person_for_author(book.author)
        elif book.author_name:
            person = person_for_name(book.author_name)
        else:
            person = None
        if person is not None:
            Contribution.objects.create(work=work, person=person, role="AUTHOR", position=0)

        edition = Edition.objects.create(
            work=work,
            language=language,
            publication_year=book.published_year,
            page_count=book.pages,
            cover_image=book.cover_image.name if book.cover_image else "",
            source=manual,
        )

        if book.pdf_file:
            AccessLink.objects.create(
                edition=edition,
                source=manual,
                link_type="DOWNLOAD",
                hosted_file=book.pdf_file.name,
                access_status="UNKNOWN",
                rights_status="UNKNOWN",
                verification_status="UNVERIFIED",
                rights_evidence="ملف مرفوع في النسخة الأولى من الموقع دون توثيق للحقوق. لا يُتاح حتى التحقق.",
            )
        imported += 1

    return imported
