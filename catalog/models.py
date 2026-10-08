"""نموذج بيانات الفهرس.

Work     : العمل الفكري المجرد (مثل "Clean Code") بغض النظر عن الطبعة أو اللغة.
Edition  : تجسيد محدد للعمل (طبعة، لغة، ناشر، ISBN).
Person   : مؤلف/محرر/مترجم. لا تُخترع أي معلومة: كل الحقول اختيارية.
AccessLink: طريقة وصول قانونية لطبعة (قراءة، تحميل، شراء، معاينة) مع حالة الحقوق.
WorkTranslation: يربط عملًا أصليًا بعمل مترجم بعد التحقق.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from core.arabic import normalize_key
from core.validators import validate_image_file, validate_pdf_file

from .identifiers import (
    clean_isbn,
    normalize_doi,
    validate_doi,
    validate_isbn10,
    validate_isbn13,
    validate_orcid,
)

# ======================================================================
# Enumerations
# ======================================================================


class ContentType(models.TextChoices):
    BOOK = "BOOK", "كتاب"
    TEXTBOOK = "TEXTBOOK", "كتاب دراسي"
    REFERENCE = "REFERENCE", "مرجع"
    RESEARCH_PAPER = "RESEARCH_PAPER", "بحث علمي"
    PREPRINT = "PREPRINT", "نسخة أولية (Preprint)"
    THESIS = "THESIS", "رسالة علمية"
    TECHNICAL_REPORT = "TECHNICAL_REPORT", "تقرير تقني"
    DOCUMENTATION = "DOCUMENTATION", "توثيق تقني"
    MANUAL = "MANUAL", "دليل"
    COURSE = "COURSE", "مقرر/دورة"
    LECTURE_NOTES = "LECTURE_NOTES", "ملاحظات محاضرات"
    DATASET = "DATASET", "مجموعة بيانات"
    STANDARD = "STANDARD", "معيار"
    PATENT = "PATENT", "براءة اختراع"
    GOVERNMENT_PUBLICATION = "GOVERNMENT_PUBLICATION", "منشور حكومي"
    UNIVERSITY_PUBLICATION = "UNIVERSITY_PUBLICATION", "منشور جامعي"
    AUTHOR_MANUSCRIPT = "AUTHOR_MANUSCRIPT", "مخطوطة المؤلف"


class AccessStatus(models.TextChoices):
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN", "ملكية عامة"
    OPEN_ACCESS = "OPEN_ACCESS", "وصول مفتوح"
    CREATIVE_COMMONS = "CREATIVE_COMMONS", "رخصة المشاع الإبداعي"
    AUTHOR_PROVIDED = "AUTHOR_PROVIDED", "نسخة من المؤلف"
    OFFICIAL_FREE = "OFFICIAL_FREE", "مجاني من الجهة الرسمية"
    INSTITUTIONAL_ACCESS = "INSTITUTIONAL_ACCESS", "وصول مؤسسي"
    PREVIEW_ONLY = "PREVIEW_ONLY", "معاينة فقط"
    PAID = "PAID", "مدفوع"
    METADATA_ONLY = "METADATA_ONLY", "بيانات وصفية فقط"
    UNKNOWN = "UNKNOWN", "غير معروف"


# الحالات التي تسمح بالقراءة/التحميل المجاني القانوني (بشرط التحقق)
FREE_ACCESS_STATUSES = frozenset(
    {
        AccessStatus.PUBLIC_DOMAIN,
        AccessStatus.OPEN_ACCESS,
        AccessStatus.CREATIVE_COMMONS,
        AccessStatus.AUTHOR_PROVIDED,
        AccessStatus.OFFICIAL_FREE,
    }
)


class RightsStatus(models.TextChoices):
    VERIFIED_FREE = "VERIFIED_FREE", "تم التحقق: يُسمح بالتوزيع"
    VERIFIED_RESTRICTED = "VERIFIED_RESTRICTED", "تم التحقق: محمي"
    UNKNOWN = "UNKNOWN", "غير معروف"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "غير مُتحقق"
    VERIFIED = "VERIFIED", "مُتحقق"
    DISPUTED = "DISPUTED", "متنازع عليه"
    REJECTED = "REJECTED", "مرفوض"


class Difficulty(models.TextChoices):
    UNKNOWN = "", "غير محدد"
    BEGINNER = "BEGINNER", "مبتدئ"
    INTERMEDIATE = "INTERMEDIATE", "متوسط"
    ADVANCED = "ADVANCED", "متقدم"


LANGUAGE_CHOICES = [
    ("ar", "العربية"),
    ("en", "الإنجليزية"),
    ("fr", "الفرنسية"),
    ("de", "الألمانية"),
    ("es", "الإسبانية"),
    ("tr", "التركية"),
    ("fa", "الفارسية"),
    ("ur", "الأردية"),
    ("ru", "الروسية"),
    ("zh", "الصينية"),
    ("ja", "اليابانية"),
    ("other", "أخرى"),
]


def unique_slug(instance, value, max_length=200, field="slug"):
    base = slugify(value, allow_unicode=True)[:max_length] or "item"
    slug, n = base, 2
    qs = type(instance)._default_manager.exclude(pk=instance.pk)
    while qs.filter(**{field: slug}).exists():
        suffix = f"-{n}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        n += 1
    return slug


class TimeStamped(models.Model):
    created_at = models.DateTimeField("أُنشئ", auto_now_add=True)
    updated_at = models.DateTimeField("عُدّل", auto_now=True)

    class Meta:
        abstract = True


class Verifiable(models.Model):
    verification_status = models.CharField(
        "حالة التحقق",
        max_length=12,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        db_index=True,
    )
    verified_at = models.DateTimeField("تاريخ التحقق", null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="تحقق بواسطة",
    )
    last_checked_at = models.DateTimeField("آخر فحص", null=True, blank=True)

    class Meta:
        abstract = True

    def mark_verified(self, user=None):
        self.verification_status = VerificationStatus.VERIFIED
        self.verified_at = timezone.now()
        self.verified_by = user


# ======================================================================
# Taxonomy
# ======================================================================


class Subject(TimeStamped):
    """تصنيف هرمي قابل للتوسع من لوحة الإدارة."""

    name = models.CharField("الاسم بالعربية", max_length=150)
    name_en = models.CharField("الاسم بالإنجليزية", max_length=150, blank=True)
    slug = models.SlugField(max_length=150, unique=True, allow_unicode=True)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children", verbose_name="الأب"
    )
    description = models.TextField("الوصف", blank=True)
    normalized_name = models.CharField(max_length=300, editable=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        verbose_name = "موضوع"
        verbose_name_plural = "الموضوعات والتصنيفات"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name_en or self.name, 150)
        self.normalized_name = normalize_key(f"{self.name} {self.name_en}")
        super().save(*args, **kwargs)

    def ancestors(self):
        node, chain = self.parent, []
        while node is not None and node not in chain:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))


# ======================================================================
# People and organizations
# ======================================================================


class Person(TimeStamped):
    name = models.CharField("الاسم", max_length=255)
    native_name = models.CharField("الاسم بلغته الأصلية", max_length=255, blank=True)
    normalized_name = models.CharField(max_length=500, editable=False, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    bio = models.TextField("نبذة", blank=True)
    photo = models.ImageField("صورة", upload_to="people/", blank=True, null=True, validators=[validate_image_file])
    birth_year = models.SmallIntegerField("سنة الميلاد", null=True, blank=True)
    death_year = models.SmallIntegerField("سنة الوفاة", null=True, blank=True)
    nationality = models.CharField("الجنسية", max_length=100, blank=True, help_text="فقط من مصدر موثق.")
    website = models.URLField("الموقع", blank=True)
    orcid = models.CharField("ORCID", max_length=19, blank=True, validators=[validate_orcid])
    openalex_id = models.CharField("OpenAlex ID", max_length=50, blank=True)
    semantic_scholar_id = models.CharField("Semantic Scholar ID", max_length=50, blank=True)
    wikipedia_url = models.URLField("ويكيبيديا", blank=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="people", verbose_name="المجالات")
    is_featured = models.BooleanField("مميز", default=False)
    # مصدر المعلومات عن الشخص (للشفافية)
    info_source = models.CharField("مصدر المعلومات", max_length=255, blank=True)

    class Meta:
        verbose_name = "شخص"
        verbose_name_plural = "المؤلفون والمساهمون"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["orcid"], condition=~models.Q(orcid=""), name="unique_person_orcid"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, 255)
        self.normalized_name = normalize_key(f"{self.name} {self.native_name}")
        super().save(*args, **kwargs)


class Publisher(TimeStamped):
    name = models.CharField("الاسم", max_length=255)
    normalized_name = models.CharField(max_length=500, editable=False, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    website = models.URLField("الموقع", blank=True)
    country = models.CharField("الدولة", max_length=100, blank=True)

    class Meta:
        verbose_name = "ناشر"
        verbose_name_plural = "الناشرون"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, 255)
        self.normalized_name = normalize_key(self.name)
        super().save(*args, **kwargs)


class Series(TimeStamped):
    name = models.CharField("الاسم", max_length=255)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الناشر")

    class Meta:
        verbose_name = "سلسلة"
        verbose_name_plural = "السلاسل"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ======================================================================
# Works and editions
# ======================================================================


class Work(TimeStamped, Verifiable):
    title = models.CharField("العنوان", max_length=500)
    subtitle = models.CharField("العنوان الفرعي", max_length=500, blank=True)
    original_title = models.CharField("العنوان الأصلي", max_length=500, blank=True)
    normalized_title = models.CharField(max_length=1000, editable=False, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = models.TextField("الوصف", blank=True)
    why_it_matters = models.TextField("لماذا هذا المصدر مهم؟", blank=True)
    content_type = models.CharField(
        "نوع المحتوى", max_length=30, choices=ContentType.choices, default=ContentType.BOOK, db_index=True
    )
    original_language = models.CharField("اللغة الأصلية", max_length=10, choices=LANGUAGE_CHOICES, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="works", verbose_name="الموضوعات")
    keywords = models.JSONField("كلمات مفتاحية", default=list, blank=True)
    difficulty = models.CharField("المستوى", max_length=12, choices=Difficulty.choices, blank=True)
    first_publication_year = models.SmallIntegerField("سنة أول نشر", null=True, blank=True)
    doi = models.CharField("DOI", max_length=255, blank=True, db_index=True, validators=[validate_doi])
    external_ids = models.JSONField(
        "معرّفات خارجية", default=dict, blank=True, help_text='مثال: {"openalex": "W123", "openlibrary": "OL1W"}'
    )
    is_featured = models.BooleanField("مميز", default=False)
    view_count = models.PositiveIntegerField("المشاهدات", default=0, editable=False)
    # ربط مؤقت بالنموذج القديم أثناء الانتقال
    legacy_book = models.OneToOneField(
        "books.Book", on_delete=models.SET_NULL, null=True, blank=True, related_name="work", editable=False
    )

    class Meta:
        verbose_name = "عمل"
        verbose_name_plural = "الأعمال"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "original_language"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, 255)
        self.doi = normalize_doi(self.doi) if self.doi else ""
        self.normalized_title = normalize_key(" ".join(filter(None, [self.title, self.subtitle, self.original_title])))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("book_detail", kwargs={"slug": self.slug})

    @property
    def authors(self):
        return [c.person for c in self.contributions.all() if c.role == Contribution.Role.AUTHOR]

    def preferred_edition(self, language="ar"):
        """الطبعة العربية أولًا إن وُجدت، ثم الأحدث."""
        editions = list(self.editions.all())
        if not editions:
            return None
        editions.sort(key=lambda e: (e.language != language, -(e.publication_year or 0)))
        return editions[0]


class Edition(TimeStamped, Verifiable):
    class Format(models.TextChoices):
        UNKNOWN = "", "غير محدد"
        PRINT = "PRINT", "مطبوع"
        DIGITAL = "DIGITAL", "رقمي"
        BOTH = "BOTH", "مطبوع ورقمي"

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="editions", verbose_name="العمل")
    title = models.CharField("عنوان الطبعة", max_length=500, blank=True, help_text="إن اختلف عن عنوان العمل.")
    subtitle = models.CharField("العنوان الفرعي", max_length=500, blank=True)
    edition_statement = models.CharField("الطبعة", max_length=100, blank=True, help_text="مثال: الطبعة الثانية")
    language = models.CharField("اللغة", max_length=10, choices=LANGUAGE_CHOICES, blank=True, db_index=True)
    publisher = models.ForeignKey(
        Publisher, on_delete=models.SET_NULL, null=True, blank=True, related_name="editions", verbose_name="الناشر"
    )
    series = models.ForeignKey(
        Series, on_delete=models.SET_NULL, null=True, blank=True, related_name="editions", verbose_name="السلسلة"
    )
    volume = models.CharField("المجلد", max_length=50, blank=True)
    publication_date = models.DateField("تاريخ النشر", null=True, blank=True)
    publication_year = models.SmallIntegerField(
        "سنة النشر", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(2100)], db_index=True
    )
    page_count = models.PositiveIntegerField("عدد الصفحات", null=True, blank=True)
    format = models.CharField("الشكل", max_length=10, choices=Format.choices, blank=True)
    isbn10 = models.CharField("ISBN-10", max_length=10, blank=True, db_index=True, validators=[validate_isbn10])
    isbn13 = models.CharField("ISBN-13", max_length=13, blank=True, db_index=True, validators=[validate_isbn13])
    doi = models.CharField("DOI", max_length=255, blank=True, db_index=True, validators=[validate_doi])
    cover_image = models.ImageField(
        "الغلاف", upload_to="covers/", blank=True, null=True, validators=[validate_image_file]
    )
    cover_url = models.URLField("رابط الغلاف", blank=True, max_length=1000)
    source = models.ForeignKey(
        "sources.Source",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="editions",
        verbose_name="المصدر",
    )
    source_record_id = models.CharField("المعرّف في المصدر", max_length=255, blank=True)
    source_url = models.URLField("رابط السجل في المصدر", blank=True, max_length=1000)
    external_ids = models.JSONField("معرّفات خارجية", default=dict, blank=True)

    class Meta:
        verbose_name = "طبعة"
        verbose_name_plural = "الطبعات"
        ordering = ["-publication_year", "-created_at"]
        constraints = [
            # نفس السجل من نفس المصدر لا يُستورد مرتين (idempotent import)
            models.UniqueConstraint(
                fields=["source", "source_record_id"],
                condition=~models.Q(source_record_id=""),
                name="unique_edition_per_source_record",
            ),
        ]

    def __str__(self):
        label = self.display_title
        if self.edition_statement:
            label += f" ({self.edition_statement})"
        return label

    def save(self, *args, **kwargs):
        self.isbn10 = clean_isbn(self.isbn10)
        self.isbn13 = clean_isbn(self.isbn13)
        self.doi = normalize_doi(self.doi) if self.doi else ""
        if self.publication_date and not self.publication_year:
            self.publication_year = self.publication_date.year
        super().save(*args, **kwargs)

    @property
    def display_title(self):
        return self.title or self.work.title

    @property
    def access_summary(self):
        """أفضل حالة وصول متاحة لهذه الطبعة (للعرض)."""
        links = [link for link in self.access_links.all() if link.is_active]
        if not links:
            return AccessStatus.METADATA_ONLY
        for link in links:
            if link.allows_free_access:
                return link.access_status
        known = [link.access_status for link in links if link.access_status != AccessStatus.UNKNOWN]
        return known[0] if known else AccessStatus.UNKNOWN


class Contribution(models.Model):
    class Role(models.TextChoices):
        AUTHOR = "AUTHOR", "مؤلف"
        EDITOR = "EDITOR", "محرر"
        TRANSLATOR = "TRANSLATOR", "مترجم"
        ILLUSTRATOR = "ILLUSTRATOR", "رسام"
        CONTRIBUTOR = "CONTRIBUTOR", "مساهم"

    work = models.ForeignKey(
        Work, on_delete=models.CASCADE, null=True, blank=True, related_name="contributions", verbose_name="العمل"
    )
    edition = models.ForeignKey(
        Edition,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contributions",
        verbose_name="الطبعة",
        help_text="للمترجم/المحرر الخاص بطبعة بعينها.",
    )
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="contributions", verbose_name="الشخص")
    role = models.CharField("الدور", max_length=12, choices=Role.choices, default=Role.AUTHOR)
    position = models.PositiveSmallIntegerField("الترتيب", default=0)

    class Meta:
        verbose_name = "مساهمة"
        verbose_name_plural = "المساهمات"
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(work__isnull=False) | models.Q(edition__isnull=False),
                name="contribution_has_target",
            ),
            models.UniqueConstraint(
                fields=["work", "person", "role"], condition=models.Q(edition__isnull=True), name="unique_work_role"
            ),
        ]

    def __str__(self):
        return f"{self.person} ({self.get_role_display()})"


class WorkTranslation(TimeStamped, Verifiable):
    """ترجمة عمل إلى لغة أخرى. لا تُعرض إلا بعد التحقق."""

    original = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="translations", verbose_name="الأصل")
    translated = models.ForeignKey(
        Work, on_delete=models.CASCADE, related_name="translated_from", verbose_name="الترجمة"
    )
    language = models.CharField("لغة الترجمة", max_length=10, choices=LANGUAGE_CHOICES)
    translator = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="translations", verbose_name="المترجم"
    )
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الناشر")
    year = models.SmallIntegerField("السنة", null=True, blank=True)
    evidence = models.TextField("دليل التحقق", blank=True, help_text="رابط أو مرجع يثبت أن هذه ترجمة لذلك العمل.")

    class Meta:
        verbose_name = "ترجمة"
        verbose_name_plural = "الترجمات"
        constraints = [
            models.UniqueConstraint(fields=["original", "translated"], name="unique_translation_pair"),
            models.CheckConstraint(condition=~models.Q(original=models.F("translated")), name="translation_not_self"),
        ]

    def __str__(self):
        return f"{self.original} → {self.translated} ({self.language})"


# ======================================================================
# Access
# ======================================================================


class AccessLink(TimeStamped, Verifiable):
    """طريقة وصول قانونية إلى طبعة."""

    class LinkType(models.TextChoices):
        READ_ONLINE = "READ_ONLINE", "قراءة على الإنترنت"
        DOWNLOAD = "DOWNLOAD", "تحميل"
        OFFICIAL_PAGE = "OFFICIAL_PAGE", "الصفحة الرسمية"
        PURCHASE = "PURCHASE", "شراء"
        PREVIEW = "PREVIEW", "معاينة"
        LIBRARY_LOAN = "LIBRARY_LOAN", "استعارة من مكتبة"

    edition = models.ForeignKey(Edition, on_delete=models.CASCADE, related_name="access_links", verbose_name="الطبعة")
    source = models.ForeignKey(
        "sources.Source",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="access_links",
        verbose_name="المصدر",
    )
    link_type = models.CharField("نوع الرابط", max_length=15, choices=LinkType.choices)
    url = models.URLField("الرابط", blank=True, max_length=2000)
    hosted_file = models.FileField(
        "ملف مستضاف",
        upload_to="books/pdfs/",
        blank=True,
        default="",
        validators=[validate_pdf_file],
        help_text="يُتاح للتحميل فقط إذا سمحت حالة الوصول والحقوق بذلك وتم التحقق.",
    )
    access_status = models.CharField(
        "حالة الوصول", max_length=22, choices=AccessStatus.choices, default=AccessStatus.UNKNOWN, db_index=True
    )
    rights_status = models.CharField(
        "حالة الحقوق", max_length=20, choices=RightsStatus.choices, default=RightsStatus.UNKNOWN
    )
    license = models.CharField("الرخصة", max_length=100, blank=True, help_text="مثال: CC BY 4.0، Public Domain")
    license_url = models.URLField("رابط الرخصة", blank=True)
    source_owner = models.CharField("مالك المحتوى", max_length=255, blank=True)
    rights_evidence = models.TextField(
        "دليل الحقوق", blank=True, help_text="لماذا نعتبر هذه الحالة صحيحة؟ (رابط الرخصة، إذن المؤلف، ...)"
    )
    is_active = models.BooleanField("مفعّل", default=True)

    # فحص الروابط
    http_status = models.PositiveSmallIntegerField("آخر رمز HTTP", null=True, blank=True)
    is_broken = models.BooleanField("رابط معطل", default=False, db_index=True)
    failure_count = models.PositiveSmallIntegerField("مرات الفشل المتتالية", default=0)

    class Meta:
        verbose_name = "رابط وصول"
        verbose_name_plural = "روابط الوصول"
        ordering = ["link_type", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(url="") | ~models.Q(hosted_file=""),
                name="access_link_has_url_or_file",
            ),
        ]

    def __str__(self):
        return f"{self.get_link_type_display()}: {self.edition}"

    @property
    def allows_free_access(self):
        """قراءة/تحميل مجاني قانوني: حالة وصول مجانية + موثّقة + غير معطل."""
        return (
            self.is_active
            and not self.is_broken
            and self.access_status in FREE_ACCESS_STATUSES
            and self.verification_status == VerificationStatus.VERIFIED
        )

    @property
    def can_serve_hosted_file(self):
        """نستضيف الملف فقط مع حقوق موثقة تسمح بالتوزيع."""
        return bool(self.hosted_file) and self.allows_free_access and self.rights_status == RightsStatus.VERIFIED_FREE

    @property
    def is_trusted(self):
        return self.access_status != AccessStatus.UNKNOWN and self.verification_status == VerificationStatus.VERIFIED
