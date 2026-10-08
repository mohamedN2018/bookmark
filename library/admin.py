from django.contrib import admin

from .models import Rating, ReadingEntry, SavedWork


@admin.register(SavedWork)
class SavedWorkAdmin(admin.ModelAdmin):
    list_display = ("user", "work", "created_at")
    search_fields = ("user__username", "work__title")
    raw_id_fields = ("user", "work")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("user", "work", "score", "updated_at")
    list_filter = ("score",)
    search_fields = ("user__username", "work__title", "comment")
    raw_id_fields = ("user", "work")


@admin.register(ReadingEntry)
class ReadingEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "work", "open_count", "last_opened_at")
    search_fields = ("user__username", "work__title")
    raw_id_fields = ("user", "work")
