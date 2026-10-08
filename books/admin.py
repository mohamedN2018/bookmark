from django.contrib import admin

from .models import Author, Book, Bookmark, Category, ReadingHistory, Review, UserActivity


# ===================== Category =====================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_at",)
    ordering = ("name",)


# ===================== Author =====================
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "books_count", "is_featured", "created_at")
    list_filter = ("is_featured", "specialization", "created_at")
    search_fields = ("name", "specialization", "bio")
    list_editable = ("is_featured",)

    def books_count(self, obj):
        return obj.books.count()

    books_count.short_description = "عدد الكتب"


# ===================== Book =====================
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "published_year", "is_free", "is_featured", "created_at")

    list_filter = ("category", "is_free", "is_featured", "language", "created_at")

    search_fields = (
        "title",
        "author__name",  # ✅ تصحيح مهم
        "description",
    )

    prepopulated_fields = {"slug": ("title",)}

    autocomplete_fields = ("author", "category")

    readonly_fields = ("views", "downloads", "created_at", "updated_at")

    fieldsets = (
        ("📘 معلومات الكتاب", {"fields": ("title", "slug", "author", "category", "description")}),
        ("🖼️ الملفات", {"fields": ("cover_image", "pdf_file")}),
        ("⚙️ معلومات فنية", {"fields": ("published_year", "pages", "language", "file_format")}),
        ("💰 السعر", {"fields": ("price", "is_free")}),
        ("⭐ الإعدادات", {"fields": ("is_featured",)}),
        ("📊 الإحصائيات", {"fields": ("views", "downloads", "created_at", "updated_at")}),
    )


# ===================== Review =====================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("book__title", "user__username", "comment")
    ordering = ("-created_at",)


# ===================== Bookmark =====================
@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "book__title")


# ===================== Reading History =====================
@admin.register(ReadingHistory)
class ReadingHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "progress", "last_read")
    list_filter = ("last_read",)
    search_fields = ("user__username", "book__title")
    readonly_fields = ("last_read",)


# ===================== User Activity =====================
@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "visited_at")
    list_filter = ("activity_type", "visited_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "activity_type", "details", "visited_at")
