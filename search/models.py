from django.core.cache import cache
from django.db import models

from core.arabic import normalize_key


class SearchSettings(models.Model):
    """أوزان ترتيب النتائج. سجل واحد يُعدَّل من لوحة الإدارة."""

    title_weight = models.FloatField("وزن تطابق العنوان", default=3.0)
    text_weight = models.FloatField("وزن تطابق النص الكامل", default=2.0)
    free_access_bonus = models.FloatField("مكافأة الوصول المجاني الموثّق", default=0.4)
    verified_bonus = models.FloatField("مكافأة البيانات المُتحقق منها", default=0.2)
    arabic_bonus = models.FloatField("مكافأة المحتوى العربي", default=0.5)
    recency_weight = models.FloatField("وزن الحداثة", default=0.1)
    typo_threshold = models.FloatField(
        "حد التشابه لتحمّل الأخطاء", default=0.45, help_text="0-1. الأقل = تساهل أكبر مع الأخطاء الإملائية."
    )
    updated_at = models.DateTimeField(auto_now=True)

    CACHE_KEY = "search-settings"

    class Meta:
        verbose_name = "إعدادات ترتيب البحث"
        verbose_name_plural = "إعدادات ترتيب البحث"

    def __str__(self):
        return "إعدادات ترتيب البحث"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    @classmethod
    def current(cls):
        settings = cache.get(cls.CACHE_KEY)
        if settings is None:
            settings, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, settings, 300)
        return settings


class Synonym(models.Model):
    """مجموعة مصطلحات متكافئة في البحث (عربي/إنجليزي/اختصارات)."""

    terms = models.TextField(
        "المصطلحات", help_text="مصطلح في كل سطر، مثل: الذكاء الاصطناعي / artificial intelligence / AI"
    )
    is_active = models.BooleanField("مفعّل", default=True)

    CACHE_KEY = "search-synonyms"

    class Meta:
        verbose_name = "مرادفات"
        verbose_name_plural = "المرادفات"

    def __str__(self):
        return " = ".join(self.term_list()[:4])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete(self.CACHE_KEY)
        return result

    def term_list(self):
        return [t.strip() for t in self.terms.replace("،", "\n").replace(",", "\n").splitlines() if t.strip()]

    @classmethod
    def groups(cls):
        """[[مصطلح مطبّع, ...], ...] من الذاكرة المؤقتة."""
        groups = cache.get(cls.CACHE_KEY)
        if groups is None:
            groups = []
            for synonym in cls.objects.filter(is_active=True):
                normalized = [normalize_key(t) for t in synonym.term_list()]
                normalized = [t for t in dict.fromkeys(normalized) if t]
                if len(normalized) > 1:
                    groups.append(normalized)
            cache.set(cls.CACHE_KEY, groups, 300)
        return groups


class SearchLog(models.Model):
    """سجل بحث مجهول الهوية: لا مستخدم، لا IP. لمعرفة ما يبحث عنه الناس وما ينقص المكتبة."""

    query = models.CharField("نص البحث", max_length=200)
    normalized_query = models.CharField("النص المطبّع", max_length=200, db_index=True)
    results = models.PositiveIntegerField("عدد النتائج")
    filters = models.JSONField("التصفية", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "عملية بحث"
        verbose_name_plural = "سجل البحث"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["results", "created_at"])]

    def __str__(self):
        return f"{self.query} ({self.results})"
