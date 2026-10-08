from django.db import models
from django.utils.text import slugify


class Source(models.Model):
    """مصدر للبيانات أو المحتوى (مكتبة، مستودع، ناشر، ...).

    كل سجل في الفهرس يشير إلى المصدر الذي جاء منه. منطق الاتصال الفعلي
    (search/fetch/normalize) يُعرّف في sources.providers ويُربط عبر provider_key.
    """

    class SourceType(models.TextChoices):
        LIBRARY = "LIBRARY", "مكتبة"
        REPOSITORY = "REPOSITORY", "مستودع"
        AGGREGATOR = "AGGREGATOR", "مُجمِّع بيانات"
        PUBLISHER = "PUBLISHER", "ناشر"
        UNIVERSITY = "UNIVERSITY", "جامعة"
        GOVERNMENT = "GOVERNMENT", "جهة حكومية"
        AUTHOR = "AUTHOR", "المؤلف"
        MANUAL = "MANUAL", "إدخال يدوي"
        OTHER = "OTHER", "أخرى"

    class Health(models.TextChoices):
        UNKNOWN = "UNKNOWN", "غير معروف"
        OK = "OK", "يعمل"
        DEGRADED = "DEGRADED", "متقطع"
        DOWN = "DOWN", "متوقف"

    name = models.CharField("الاسم", max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    provider_key = models.CharField(
        "مفتاح المزوّد",
        max_length=50,
        blank=True,
        help_text="يربط المصدر بتنفيذ SourceProvider في الكود (فارغ للإدخال اليدوي).",
    )
    source_type = models.CharField("النوع", max_length=20, choices=SourceType.choices, default=SourceType.OTHER)
    owner = models.CharField("الجهة المالكة", max_length=200, blank=True)
    domain = models.CharField("النطاق", max_length=200, blank=True)
    homepage_url = models.URLField("الموقع", blank=True)

    has_api = models.BooleanField("يوفر API", default=False)
    supports_search = models.BooleanField("يدعم البحث", default=False)
    supports_metadata = models.BooleanField("يوفر بيانات وصفية", default=False)

    legal_access_policy = models.TextField(
        "سياسة الوصول القانونية",
        blank=True,
        help_text="ما المسموح: فهرسة البيانات؟ الربط؟ إعادة الاستضافة؟ مع رابط الشروط.",
    )
    allows_rehosting = models.BooleanField(
        "يسمح بإعادة الاستضافة",
        default=False,
        help_text="لا تفعّله إلا بوجود نص صريح في شروط المصدر أو رخصة المحتوى.",
    )
    terms_url = models.URLField("رابط الشروط", blank=True)
    metadata_license = models.CharField("رخصة البيانات الوصفية", max_length=100, blank=True)

    rate_limit_per_minute = models.PositiveIntegerField("حد الطلبات/دقيقة", null=True, blank=True)
    priority = models.PositiveSmallIntegerField("الأولوية", default=50, help_text="الأعلى أولًا عند التعارض.")
    reliability = models.PositiveSmallIntegerField(
        "الموثوقية (0-100)", default=50, help_text="تدخل في ترتيب نتائج البحث وجودة البيانات."
    )
    is_active = models.BooleanField("مفعّل", default=True)

    health_status = models.CharField("الحالة", max_length=10, choices=Health.choices, default=Health.UNKNOWN)
    last_health_check_at = models.DateTimeField("آخر فحص", null=True, blank=True)
    last_synced_at = models.DateTimeField("آخر مزامنة", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مصدر"
        verbose_name_plural = "المصادر"
        ordering = ["-priority", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:100]
        super().save(*args, **kwargs)
