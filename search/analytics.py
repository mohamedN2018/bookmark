"""تحليلات البحث مجهولة الهوية (لا مستخدم ولا IP)."""

from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone

from .models import SearchLog

BOT_MARKERS = ("bot", "crawl", "spider", "slurp", "preview")


def is_bot(request):
    agent = request.META.get("HTTP_USER_AGENT", "").lower()
    return not agent or any(marker in agent for marker in BOT_MARKERS)


def log_search(request, query, normalized, results, filters=None):
    if not normalized or is_bot(request) or request.GET.get("page"):
        return
    SearchLog.objects.create(
        query=query[:200], normalized_query=normalized[:200], results=results, filters=filters or {}
    )


def top_queries(days=30, limit=10, zero_results=False, min_count=1):
    since = timezone.now() - timedelta(days=days)
    qs = SearchLog.objects.filter(created_at__gte=since)
    qs = qs.filter(results=0) if zero_results else qs.filter(results__gt=0)
    return (
        qs.values("normalized_query")
        .annotate(count=Count("id"), example=Max("query"), last=Max("created_at"))
        .filter(count__gte=min_count)
        .order_by("-count", "-last")[:limit]
    )
