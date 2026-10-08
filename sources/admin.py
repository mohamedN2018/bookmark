from django.contrib import admin

from .models import ImportJob, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "provider_key",
        "has_api",
        "allows_rehosting",
        "reliability",
        "health_status",
        "is_active",
        "last_synced_at",
    )
    list_filter = ("source_type", "health_status", "is_active", "has_api", "allows_rehosting")
    search_fields = ("name", "domain", "owner")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("last_health_check_at", "last_synced_at", "created_at", "updated_at")


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "status",
        "started_at",
        "finished_at",
        "seen",
        "created",
        "updated",
        "duplicates",
        "skipped",
        "files_downloaded",
        "errors",
    )
    list_filter = ("source", "status")
    readonly_fields = [f.name for f in ImportJob._meta.fields]

    def has_add_permission(self, request):
        return False
