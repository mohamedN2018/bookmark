"""محرك البحث.

1. معرّفات: ISBN-10/13 أو DOI → مطابقة مباشرة.
2. التطبيع: core.arabic.normalize_key (همزات، ى/ي، ة/ه، تشكيل، "ال"، أرقام، lowercase).
3. المرادفات: كل مجموعة في search.Synonym تولّد صيغًا بديلة للاستعلام (عربي ↔ إنجليزي ↔ اختصار).
4. المطابقة:
   - PostgreSQL: full-text على search_vector (tsvector 'simple' على النص المطبّع)،
     كل كلمات الصيغة مطلوبة، وآخر كلمة بادئة (prefix) لدعم الإكمال التلقائي.
   - غير ذلك (SQLite للتطوير): icontains على search_document.
5. تحمّل الأخطاء: إن لم توجد نتائج، بحث بالتشابه الثلاثي (pg_trgm) على العنوان، وتُعلَّم النتائج "تقريبية".
6. الترتيب: أوزان قابلة للتعديل من الإدارة (search.SearchSettings):
   تطابق العنوان، تطابق النص، وصول مجاني موثّق، بيانات مُتحقق منها، محتوى عربي، حداثة.
"""

import re
from dataclasses import dataclass, field

from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity, TrigramStrictWordSimilarity
from django.db import connection
from django.db.models import Case, Exists, F, FloatField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast, Coalesce, Least

from catalog.identifiers import clean_isbn, is_valid_isbn10, is_valid_isbn13, normalize_doi
from catalog.models import (
    FREE_ACCESS_STATUSES,
    AccessLink,
    AccessStatus,
    Edition,
    Subject,
    VerificationStatus,
    Work,
)
from core.arabic import normalize_key

from .models import SearchSettings, Synonym

MAX_QUERY_LENGTH = 200
MAX_VARIANTS = 8
_WORD = re.compile(r"^\w+$")

ORDERINGS = {
    "relevance": None,
    "newest": ["-created_at"],
    "year": ["-latest_year", "-created_at"],
    "title": ["normalized_title"],
}


@dataclass
class SearchResult:
    queryset: object
    query: str = ""
    normalized: str = ""
    variants: list = field(default_factory=list)
    approximate: bool = False
    identifier: bool = False


def is_postgres():
    return connection.vendor == "postgresql"


# ---------------------------------------------------------------- query parsing


def expand_query(normalized):
    """صيغ بديلة للاستعلام عبر المرادفات. الصيغة الأصلية أولًا."""
    variants = [normalized]
    padded = f" {normalized} "
    for group in Synonym.groups():
        for term in group:
            if f" {term} " in padded:
                for alternative in group:
                    if alternative != term:
                        variant = f" {padded} ".replace(f" {term} ", f" {alternative} ").split()
                        variants.append(" ".join(variant))
                break
    return list(dict.fromkeys(v for v in variants if v))[:MAX_VARIANTS]


def _identifier_q(query):
    isbn = clean_isbn(query)
    if is_valid_isbn13(isbn):
        return Q(id__in=Edition.objects.filter(isbn13=isbn).values("work_id"))
    if is_valid_isbn10(isbn):
        return Q(id__in=Edition.objects.filter(isbn10=isbn).values("work_id"))
    doi = normalize_doi(query)
    if doi:
        return Q(doi=doi) | Q(id__in=Edition.objects.filter(doi=doi).values("work_id"))
    return None


def _tsquery(variants, prefix=True):
    groups = []
    for variant in variants:
        tokens = [t for t in variant.split() if _WORD.match(t)]
        if not tokens:
            continue
        if prefix:
            tokens[-1] = f"{tokens[-1]}:*"
        groups.append("(" + " & ".join(tokens) + ")")
    if not groups:
        return None
    return SearchQuery(" | ".join(groups), search_type="raw", config="simple")


def _contains_q(variants):
    condition = Q()
    for variant in variants:
        group = Q()
        for token in variant.split():
            group &= Q(search_document__icontains=token)
        condition |= group
    return condition


# ---------------------------------------------------------------- filters


def free_access_exists():
    return Exists(
        AccessLink.objects.filter(
            edition__work=OuterRef("pk"),
            access_status__in=list(FREE_ACCESS_STATUSES),
            verification_status=VerificationStatus.VERIFIED,
            is_active=True,
            is_broken=False,
        )
    )


def descendant_ids(subject):
    ids, frontier = [], [subject.id]
    while frontier:
        children = [
            c for c in Subject.objects.filter(parent_id__in=frontier).values_list("id", flat=True) if c not in ids
        ]
        ids.extend(children)
        frontier = children
    return ids


def apply_filters(qs, *, subject=None, language="", content_type="", access=""):
    if subject is not None:
        ids = [subject.id, *descendant_ids(subject)]
        qs = qs.filter(id__in=Work.subjects.through.objects.filter(subject_id__in=ids).values("work_id"))
    if language:
        qs = qs.filter(
            Q(original_language=language) | Q(id__in=Edition.objects.filter(language=language).values("work_id"))
        )
    if content_type:
        qs = qs.filter(content_type=content_type)
    if access == "free":
        qs = qs.filter(free_access_exists())
    elif access == "paid":
        qs = qs.filter(id__in=Edition.objects.filter(access_links__access_status=AccessStatus.PAID).values("work_id"))
    elif access == "metadata":
        qs = qs.exclude(id__in=Edition.objects.filter(access_links__is_active=True).values("work_id"))
    return qs


# ---------------------------------------------------------------- ranking


def _bonuses(settings):
    latest_year = Subquery(
        Edition.objects.filter(work=OuterRef("pk"), publication_year__isnull=False)
        .order_by("-publication_year")
        .values("publication_year")[:1]
    )
    arabic = Q(original_language="ar") | Q(id__in=Edition.objects.filter(language="ar").values("work_id"))
    return {
        "latest_year": latest_year,
        "bonus": (
            Case(When(free_access_exists(), then=Value(settings.free_access_bonus)), default=Value(0.0))
            + Case(
                When(verification_status=VerificationStatus.VERIFIED, then=Value(settings.verified_bonus)),
                default=Value(0.0),
            )
            + Case(When(arabic, then=Value(settings.arabic_bonus)), default=Value(0.0))
        ),
    }


def _recency(settings):
    # 0 لما قبل 1900، 1 لعام 2030 فأحدث
    year = Cast(Coalesce(F("latest_year"), Value(1900)), FloatField())
    return Least(year - Value(1900.0), Value(130.0)) / Value(130.0) * Value(float(settings.recency_weight))


# ---------------------------------------------------------------- main entry


def search(query="", *, subject=None, language="", content_type="", access="", order="", limit=None):
    settings = SearchSettings.current()
    base = Work.objects.exclude(verification_status=VerificationStatus.REJECTED)
    base = apply_filters(base, subject=subject, language=language, content_type=content_type, access=access)
    query = (query or "").strip()[:MAX_QUERY_LENGTH]
    normalized = normalize_key(query)
    result = SearchResult(queryset=base, query=query, normalized=normalized)

    if not normalized:
        result.queryset = base.annotate(**_bonuses(settings)).order_by(*(ORDERINGS.get(order) or ["-created_at"]))
        return result

    identifier = _identifier_q(query)
    if identifier is not None:
        result.identifier = True
        result.queryset = base.filter(identifier).annotate(**_bonuses(settings)).order_by("-created_at")
        return result

    variants = expand_query(normalized)
    result.variants = variants
    qs = base.annotate(**_bonuses(settings))

    if is_postgres():
        tsquery = _tsquery(variants)
        matched = qs.filter(search_vector=tsquery) if tsquery is not None else qs.none()
        relevance = (
            SearchRank(F("search_vector"), tsquery, cover_density=True) * Value(settings.text_weight)
            + TrigramSimilarity("normalized_title", Value(normalized)) * Value(settings.title_weight)
            if tsquery is not None
            else Value(0.0)
        )
        if not matched.exists() and len(normalized) >= 3:
            # تشابه الكلمة الصارم: يقارن الاستعلام بأقرب كلمات كاملة في العنوان (يصلح للعناوين الطويلة)
            similarity = TrigramStrictWordSimilarity(Value(normalized), "normalized_title")
            matched = qs.annotate(similarity=similarity).filter(similarity__gte=settings.typo_threshold)
            relevance = F("similarity") * Value(settings.title_weight)
            result.approximate = True
    else:
        matched = qs.filter(_contains_q(variants))
        relevance = Case(
            When(normalized_title=normalized, then=Value(3.0)),
            When(normalized_title__startswith=normalized, then=Value(2.0)),
            When(normalized_title__icontains=normalized, then=Value(1.5)),
            default=Value(1.0),
            output_field=FloatField(),
        ) * Value(settings.title_weight)

    ranked = matched.annotate(rank=relevance + F("bonus") + _recency(settings))
    default_ordering = ["-similarity", "-rank", "-created_at"] if result.approximate else ["-rank", "-created_at"]
    ordering = ORDERINGS.get(order) or default_ordering
    result.queryset = ranked.order_by(*ordering)
    if limit:
        result.queryset = result.queryset[:limit]
    return result
