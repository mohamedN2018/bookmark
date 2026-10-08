from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils.text import slugify

from core.validators import validate_image_file, validate_pdf_file


def unique_slug(instance, value, max_length):
    """slug فريد: يضيف -2، -3 ... عند التصادم بدل IntegrityError."""
    base = slugify(value, allow_unicode=True)[:max_length] or "item"
    slug, n = base, 2
    qs = type(instance).objects.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        suffix = f"-{n}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")
    features = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    description = models.TextField(blank=True, verbose_name="الوصف")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, 100)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("books_by_category", kwargs={"slug": self.slug})


class Author(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم المؤلف")
    bio = models.TextField(verbose_name="السيرة الذاتية", blank=True, null=True)
    avatar = models.ImageField(
        upload_to="authors/avatars/",
        verbose_name="الصورة الشخصية",
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    specialization = models.CharField(max_length=200, verbose_name="التخصص", blank=True, null=True)
    website = models.URLField(verbose_name="الموقع الإلكتروني", blank=True, null=True)
    email = models.EmailField(verbose_name="البريد الإلكتروني", blank=True, null=True)
    is_featured = models.BooleanField(default=False, verbose_name="مميز")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مؤلف"
        verbose_name_plural = "المؤلفون"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_books_count(self):
        return self.books.count()

    def get_total_readers(self):
        return ReadingHistory.objects.filter(book__author=self).values("user").distinct().count()

    def average_rating(self):
        avg = self.books.aggregate(avg_rating=Avg("reviews__rating"))["avg_rating"]
        return avg if avg else 0


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان الكتاب")
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    author = models.ForeignKey(
        Author, on_delete=models.SET_NULL, related_name="books", verbose_name="المؤلف", null=True, blank=True
    )
    author_name = models.CharField(max_length=100, verbose_name="اسم المؤلف (إذا لم يكن مسجلاً)", blank=True, null=True)
    description = models.TextField(verbose_name="الوصف", blank=True)
    cover_image = models.ImageField(
        upload_to="book_covers/", verbose_name="صورة الغلاف", blank=True, null=True, validators=[validate_image_file]
    )
    pdf_file = models.FileField(
        upload_to="books/pdfs/", blank=True, null=True, verbose_name="ملف PDF", validators=[validate_pdf_file]
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="books", verbose_name="التصنيف")
    # غير إلزامية: لا نجبر أحدًا على إدخال قيمة غير معروفة
    published_year = models.PositiveIntegerField(verbose_name="سنة النشر", null=True, blank=True)
    pages = models.PositiveIntegerField(verbose_name="عدد الصفحات", null=True, blank=True)
    language = models.CharField(max_length=50, verbose_name="اللغة", default="العربية")
    file_format = models.CharField(max_length=50, verbose_name="صيغة الملف", default="PDF")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر", default=0.00)
    is_free = models.BooleanField(default=False, verbose_name="مجاني")
    is_featured = models.BooleanField(default=False, verbose_name="مميز")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.IntegerField(default=0, verbose_name="عدد التحميلات")
    views = models.IntegerField(default=0, verbose_name="عدد المشاهدات")

    class Meta:
        verbose_name = "كتاب"
        verbose_name_plural = "الكتب"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, 200)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("book_detail", kwargs={"slug": self.slug})

    def average_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    @property
    def author_display(self):
        """اسم المؤلف المسجّل، أو الاسم النصي الاحتياطي، أو نص فارغ."""
        if self.author_id:
            return self.author.name
        return self.author_name or ""

    def increment_views(self):
        # تحديث ذري بدون race condition
        type(self).objects.filter(pk=self.pk).update(views=models.F("views") + 1)


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews", verbose_name="الكتاب")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="التقييم")
    comment = models.TextField(verbose_name="التعليق")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مراجعة"
        verbose_name_plural = "المراجعات"
        ordering = ["-created_at"]
        unique_together = ["book", "user"]

    def __str__(self):
        return f"مراجعة {self.user.username} على {self.book.title}"


class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_history", verbose_name="المستخدم")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    last_read = models.DateTimeField(auto_now=True, verbose_name="آخر قراءة")
    progress = models.IntegerField(default=0, verbose_name="التقدم %")
    reading_duration_minutes = models.IntegerField(default=0, verbose_name="مدة القراءة (دقيقة)")  # أضف هذا

    class Meta:
        verbose_name = "سجل القراءة"
        verbose_name_plural = "سجلات القراءة"
        ordering = ["-last_read"]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks", verbose_name="المستخدم")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إشارة مرجعية"
        verbose_name_plural = "الإشارات المرجعية"
        unique_together = ["user", "book"]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class UserActivity(models.Model):
    """تتبع نشاط المستخدمين (كان معرّفًا سابقًا داخل views.py)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ("login", "تسجيل دخول"),
            ("view_book", "عرض كتاب"),
            ("read_book", "قراءة كتاب"),
            ("review", "إضافة تقييم"),
            ("bookmark", "إضافة إشارة مرجعية"),
        ],
    )
    details = models.TextField(blank=True, null=True)
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نشاط المستخدم"
        verbose_name_plural = "أنشطة المستخدمين"
        ordering = ["-visited_at"]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.visited_at}"
