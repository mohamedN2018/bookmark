from django import template

from catalog.models import FREE_ACCESS_STATUSES, LANGUAGE_CHOICES, AccessStatus

register = template.Library()

LANGUAGE_LABELS = dict(LANGUAGE_CHOICES)

BADGE_CLASS = {
    AccessStatus.PUBLIC_DOMAIN: "badge-free",
    AccessStatus.OPEN_ACCESS: "badge-free",
    AccessStatus.CREATIVE_COMMONS: "badge-free",
    AccessStatus.AUTHOR_PROVIDED: "badge-free",
    AccessStatus.OFFICIAL_FREE: "badge-free",
    AccessStatus.INSTITUTIONAL_ACCESS: "badge-inst",
    AccessStatus.PREVIEW_ONLY: "badge-preview",
    AccessStatus.PAID: "badge-paid",
    AccessStatus.METADATA_ONLY: "",
    AccessStatus.UNKNOWN: "badge-unknown",
}

# ترتيب الأفضلية عند تلخيص عدة طبعات
ACCESS_RANK = [
    AccessStatus.PUBLIC_DOMAIN,
    AccessStatus.OPEN_ACCESS,
    AccessStatus.CREATIVE_COMMONS,
    AccessStatus.OFFICIAL_FREE,
    AccessStatus.AUTHOR_PROVIDED,
    AccessStatus.INSTITUTIONAL_ACCESS,
    AccessStatus.PREVIEW_ONLY,
    AccessStatus.PAID,
    AccessStatus.UNKNOWN,
    AccessStatus.METADATA_ONLY,
]


@register.filter
def access_class(status):
    return BADGE_CLASS.get(status, "")


@register.filter
def access_label(status):
    try:
        return AccessStatus(status).label
    except ValueError:
        return status


@register.filter
def language_label(code):
    return LANGUAGE_LABELS.get(code, code)


@register.filter
def is_free_status(status):
    return status in FREE_ACCESS_STATUSES


@register.simple_tag
def work_summary(work):
    """ملخص بطاقة العمل من البيانات المحمّلة مسبقًا (لا استعلامات إضافية)."""
    editions = list(work.editions.all())
    contributions = getattr(work, "author_contributions", None)
    if contributions is None:
        contributions = [c for c in work.contributions.all() if c.role == "AUTHOR"]
    years = [e.publication_year for e in editions if e.publication_year]
    languages = {e.language for e in editions if e.language} or ({work.original_language} - {""})
    statuses = [e.access_summary for e in editions] or [AccessStatus.METADATA_ONLY]
    best = min(statuses, key=lambda s: ACCESS_RANK.index(s) if s in ACCESS_RANK else len(ACCESS_RANK))
    return {
        "authors": [c.person for c in contributions],
        "year": min(years) if years else work.first_publication_year,
        "languages": [LANGUAGE_LABELS.get(code, code) for code in sorted(languages)],
        "access": best,
        "edition_count": len(editions),
    }
