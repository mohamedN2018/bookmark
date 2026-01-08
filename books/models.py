from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")
    features = models.TextField(blank=True, null=True)  # <--- أضفنا هذا الحقل
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    description = models.TextField(blank=True, verbose_name="الوصف")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('books_by_category', kwargs={'slug': self.slug})

class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان الكتاب")
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    author = models.CharField(max_length=100, verbose_name="المؤلف")
    description = models.TextField(verbose_name="الوصف")
    cover_image = models.ImageField(upload_to='book_covers/', verbose_name="صورة الغلاف", blank=True, null=True)
    pdf_file = models.FileField(upload_to='books/pdfs/', blank=True, null=True, verbose_name="ملف PDF")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='books', verbose_name="التصنيف")
    published_year = models.IntegerField(verbose_name="سنة النشر")
    pages = models.IntegerField(verbose_name="عدد الصفحات")
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
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('book_detail', kwargs={'slug': self.slug})
    
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum([review.rating for review in reviews]) / len(reviews)
        return 0
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def increment_downloads(self):
        self.downloads += 1
        self.save(update_fields=['downloads'])


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews', verbose_name="الكتاب")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="التقييم"
    )
    comment = models.TextField(verbose_name="التعليق")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "مراجعة"
        verbose_name_plural = "المراجعات"
        ordering = ['-created_at']
        unique_together = ['book', 'user']
    
    def __str__(self):
        return f"مراجعة {self.user.username} على {self.book.title}"

class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_history', verbose_name="المستخدم")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    last_read = models.DateTimeField(auto_now=True, verbose_name="آخر قراءة")
    progress = models.IntegerField(default=0, verbose_name="التقدم %")
    reading_duration_minutes = models.IntegerField(default=0, verbose_name="مدة القراءة (دقيقة)")  # أضف هذا

    class Meta:
        verbose_name = "سجل القراءة"
        verbose_name_plural = "سجلات القراءة"
        ordering = ['-last_read']
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks', verbose_name="المستخدم")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "إشارة مرجعية"
        verbose_name_plural = "الإشارات المرجعية"
        unique_together = ['user', 'book']
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title}"