from django.contrib import admin
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .analytics import top_queries
from .models import SearchLog, SearchSettings, Synonym


@admin.register(SearchSettings)
class SearchSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "title_weight", "text_weight", "arabic_bonus", "free_access_bonus", "updated_at")

    def has_add_permission(self, request):
        return not SearchSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings = SearchSettings.current()
        return redirect(reverse("admin:search_searchsettings_change", args=[settings.pk]))


@admin.register(Synonym)
class SynonymAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active")
    list_filter = ("is_active",)
    search_fields = ("terms",)


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "results", "created_at")
    list_filter = ("created_at",)
    search_fields = ("query", "normalized_query")
    readonly_fields = ("query", "normalized_query", "results", "filters", "created_at")
    change_list_template = "admin/search/searchlog_changelist.html"

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        custom = [path("insights/", self.admin_site.admin_view(self.insights_view), name="search_insights")]
        return custom + super().get_urls()

    def insights_view(self, request):
        days = int(request.GET.get("days", 30)) if request.GET.get("days", "30").isdigit() else 30
        context = {
            **self.admin_site.each_context(request),
            "title": "تحليلات البحث",
            "days": days,
            "top": top_queries(days=days, limit=30),
            "zero": top_queries(days=days, limit=50, zero_results=True),
            "total": SearchLog.objects.count(),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/search/insights.html", context)
