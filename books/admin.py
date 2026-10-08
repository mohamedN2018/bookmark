"""النموذج القديم (النسخة الأولى من الموقع): للقراءة فقط.

البيانات نُقلت إلى catalog و library. الإضافة والتعديل يتمان من الفهرس الجديد.
"""

from django.contrib import admin

from .models import Author, Book, Bookmark, Category, ReadingHistory, Review, UserActivity


class ReadOnlyLegacyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Book)
class BookAdmin(ReadOnlyLegacyAdmin):
    list_display = ("title", "author", "category", "published_year", "created_at")
    search_fields = ("title",)


@admin.register(Author)
class AuthorAdmin(ReadOnlyLegacyAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(ReadOnlyLegacyAdmin):
    list_display = ("name", "slug")


for model in (Review, Bookmark, ReadingHistory, UserActivity):
    admin.site.register(model, ReadOnlyLegacyAdmin)
