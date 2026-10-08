"""مكتبة المستخدم: المحفوظات، التقييمات، وسجل الفتح. كلها مرتبطة بـ Work."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SavedWork(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_works")
    work = models.ForeignKey("catalog.Work", on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مصدر محفوظ"
        verbose_name_plural = "المصادر المحفوظة"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "work"], name="unique_saved_work")]

    def __str__(self):
        return f"{self.user} ← {self.work}"


class Rating(models.Model):
    """تقييم حقيقي من مستخدم مسجّل. لا تقييمات مُنشأة آليًا."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    work = models.ForeignKey("catalog.Work", on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField("التقييم", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("تعليق", blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "work"], name="unique_rating"),
            models.CheckConstraint(condition=models.Q(score__gte=1, score__lte=5), name="rating_score_range"),
        ]

    def __str__(self):
        return f"{self.user} → {self.work}: {self.score}"


class ReadingEntry(models.Model):
    """آخر مرة فتح فيها المستخدم صفحة مصدر."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_entries")
    work = models.ForeignKey("catalog.Work", on_delete=models.CASCADE, related_name="reading_entries")
    last_opened_at = models.DateTimeField(auto_now=True)
    open_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "سجل فتح"
        verbose_name_plural = "سجل الفتح"
        ordering = ["-last_opened_at"]
        constraints = [models.UniqueConstraint(fields=["user", "work"], name="unique_reading_entry")]

    def __str__(self):
        return f"{self.user} - {self.work}"
