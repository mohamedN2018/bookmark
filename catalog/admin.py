from django.contrib import admin
from django.utils import timezone

from .models import (
    AccessLink,
    Contribution,
    Edition,
    Person,
    Publisher,
    Series,
    Subject,
    VerificationStatus,
    Work,
    WorkTranslation,
)
from .quality import quality_report


@admin.action(description="تعليم كمُتحقق منه")
def mark_verified(modeladmin, request, queryset):
    queryset.update(
        verification_status=VerificationStatus.VERIFIED, verified_at=timezone.now(), verified_by=request.user
    )


@admin.action(description="تعليم كغير مُتحقق")
def mark_unverified(modeladmin, request, queryset):
    queryset.update(verification_status=VerificationStatus.UNVERIFIED, verified_at=None, verified_by=None)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "parent", "sort_order", "is_active")
    list_filter = ("is_active", "parent")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name", "name_en", "normalized_name")
    autocomplete_fields = ("parent",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "native_name", "orcid", "is_featured", "created_at")
    list_filter = ("is_featured",)
    list_editable = ("is_featured",)
    search_fields = ("name", "native_name", "normalized_name", "orcid", "openalex_id")
    autocomplete_fields = ("subjects",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "website")
    search_fields = ("name", "normalized_name")


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("name", "publisher")
    search_fields = ("name",)
    autocomplete_fields = ("publisher",)


class ContributionInline(admin.TabularInline):
    model = Contribution
    fk_name = "work"
    extra = 0
    autocomplete_fields = ("person",)
    fields = ("person", "role", "position")


class EditionInline(admin.StackedInline):
    model = Edition
    extra = 0
    show_change_link = True
    autocomplete_fields = ("publisher", "series")
    fields = (
        ("title", "edition_statement"),
        ("language", "publication_year", "page_count"),
        ("publisher", "series"),
        ("isbn13", "isbn10", "doi"),
        ("source", "source_record_id"),
    )


class AccessLinkInline(admin.StackedInline):
    model = AccessLink
    extra = 0
    fields = (
        ("link_type", "access_status", "rights_status"),
        "url",
        "hosted_file",
        ("license", "license_url"),
        "source_owner",
        "rights_evidence",
        ("verification_status", "is_active", "is_broken"),
    )


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "content_type", "original_language", "verification_status", "quality", "created_at")
    list_filter = ("content_type", "original_language", "verification_status", "is_featured", "subjects")
    search_fields = ("title", "original_title", "normalized_title", "doi")
    autocomplete_fields = ("subjects",)
    readonly_fields = ("view_count", "quality_details", "verified_at", "verified_by", "created_at", "updated_at")
    inlines = (ContributionInline, EditionInline)
    actions = (mark_verified, mark_unverified)
    fieldsets = (
        (None, {"fields": ("title", "subtitle", "original_title", "slug", "content_type", "original_language")}),
        ("المحتوى", {"fields": ("description", "why_it_matters", "subjects", "keywords", "difficulty")}),
        ("المعرّفات", {"fields": ("doi", "first_publication_year", "external_ids")}),
        ("الإدارة", {"fields": ("is_featured", "verification_status", "verified_at", "verified_by", "view_count")}),
        ("جودة البيانات", {"fields": ("quality_details",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("editions__access_links", "contributions", "subjects")

    @admin.display(description="الجودة")
    def quality(self, obj):
        return f"{quality_report(obj)[0]}/100"

    @admin.display(description="تفاصيل الجودة")
    def quality_details(self, obj):
        if not obj.pk:
            return "-"
        score, missing = quality_report(obj)
        if not missing:
            return f"{score}/100"
        return f"{score}/100 — ناقص: " + "، ".join(missing)


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "language", "publication_year", "isbn13", "source", "verification_status")
    list_filter = ("language", "verification_status", "source", "format")
    search_fields = ("title", "work__title", "isbn13", "isbn10", "doi", "source_record_id")
    autocomplete_fields = ("work", "publisher", "series")
    inlines = (AccessLinkInline,)
    actions = (mark_verified, mark_unverified)


@admin.register(AccessLink)
class AccessLinkAdmin(admin.ModelAdmin):
    list_display = ("edition", "link_type", "access_status", "rights_status", "verification_status", "is_broken")
    list_filter = ("link_type", "access_status", "rights_status", "verification_status", "is_broken", "source")
    search_fields = ("edition__work__title", "url", "license")
    autocomplete_fields = ("edition",)
    actions = (mark_verified, mark_unverified)


@admin.register(WorkTranslation)
class WorkTranslationAdmin(admin.ModelAdmin):
    list_display = ("original", "translated", "language", "translator", "verification_status")
    list_filter = ("language", "verification_status")
    autocomplete_fields = ("original", "translated", "translator", "publisher")
    actions = (mark_verified, mark_unverified)
