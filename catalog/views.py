from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Count, F, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from books.models import Author as LegacyAuthor
from core.arabic import normalize_key

from .models import (
    LANGUAGE_CHOICES,
    AccessLink,
    ContentType,
    Contribution,
    Edition,
    Person,
    Subject,
    VerificationStatus,
    Work,
    WorkTranslation,
)
from .search import free_access_q, search_works

PAGE_SIZE = 20
SUGGEST_LIMIT = 8


def _work_list_qs(qs):
    """تحميل مسبق لكل ما تحتاجه بطاقة العمل (تجنب N+1)."""
    return qs.prefetch_related(
        Prefetch(
            "contributions",
            queryset=Contribution.objects.filter(role=Contribution.Role.AUTHOR).select_related("person"),
            to_attr="author_contributions",
        ),
        Prefetch(
            "editions",
            queryset=Edition.objects.prefetch_related("access_links").select_related("publisher"),
        ),
        "subjects",
    )


def home(request):
    works = Work.objects.exclude(verification_status=VerificationStatus.REJECTED)
    top_subjects = (
        Subject.objects.filter(parent__isnull=True, is_active=True)
        .annotate(direct=Count("works", distinct=True))
        .order_by("sort_order")
    )
    context = {
        "stats": {
            "works": works.count(),
            "people": Person.objects.count(),
            "subjects": Subject.objects.filter(is_active=True).count(),
            "free": works.filter(free_access_q()).distinct().count(),
        },
        "latest": _work_list_qs(works.order_by("-created_at"))[:8],
        "open_access": _work_list_qs(works.filter(free_access_q()).distinct().order_by("-created_at"))[:8],
        "arabic": _work_list_qs(
            works.filter(Q(original_language="ar") | Q(editions__language="ar")).distinct().order_by("-created_at")
        )[:8],
        "beginner": _work_list_qs(works.filter(difficulty="BEGINNER").order_by("-created_at"))[:8],
        "advanced": _work_list_qs(works.filter(difficulty="ADVANCED").order_by("-created_at"))[:8],
        "top_subjects": top_subjects,
        "people": Person.objects.annotate(n=Count("contributions__work", distinct=True))
        .filter(n__gt=0)
        .order_by("-is_featured", "-n", "name")[:8],
    }
    return render(request, "catalog/home.html", context)


def search(request):
    query = request.GET.get("q", "").strip()
    subject = None
    if request.GET.get("subject"):
        subject = Subject.objects.filter(slug=request.GET["subject"]).first()
    language = request.GET.get("language", "")
    content_type = request.GET.get("type", "")
    access = request.GET.get("access", "")

    results = search_works(query, subject=subject, language=language, content_type=content_type, access=access)
    page = Paginator(_work_list_qs(results.order_by("-created_at")), PAGE_SIZE).get_page(request.GET.get("page"))

    filters = request.GET.copy()
    filters.pop("page", None)

    context = {
        "query": query,
        "page_obj": page,
        "total": page.paginator.count,
        "current_subject": subject,
        "language": language,
        "content_type": content_type,
        "access": access,
        "filter_querystring": filters.urlencode(),
        "subjects": Subject.objects.filter(parent__isnull=True, is_active=True),
        "languages": LANGUAGE_CHOICES,
        "content_types": ContentType.choices,
        "external_searches": _external_searches(query) if query and page.paginator.count == 0 else [],
        "related_subjects": _related_subjects(query) if page.paginator.count == 0 else [],
    }
    return render(request, "catalog/search.html", context)


def _related_subjects(query):
    tokens = [t for t in normalize_key(query).split() if len(t) > 2]
    if not tokens:
        return []
    condition = Q()
    for token in tokens:
        condition |= Q(normalized_name__icontains=token)
    return Subject.objects.filter(condition, is_active=True)[:8]


def _external_searches(query):
    """بحث خارجي في مصادر مفتوحة وقانونية عندما لا نجد نتيجة."""
    q = quote(query)
    return [
        ("OpenAlex", f"https://openalex.org/works?search={q}"),
        ("Open Library", f"https://openlibrary.org/search?q={q}"),
        ("DOAB (كتب مفتوحة الوصول)", f"https://directory.doabooks.org/discover?query={q}"),
        ("arXiv", f"https://arxiv.org/a/search?query={q}&searchtype=all"),
        ("Project Gutenberg", f"https://www.gutenberg.org/ebooks/search/?query={q}"),
    ]


@require_GET
def search_suggest(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    works = _work_list_qs(search_works(query).order_by("-created_at"))[:SUGGEST_LIMIT]
    results = [
        {
            "title": w.title,
            "author": "، ".join(c.person.name for c in w.author_contributions),
            "url": w.get_absolute_url(),
        }
        for w in works
    ]
    return JsonResponse({"results": results})


def work_detail(request, slug):
    work = get_object_or_404(
        Work.objects.exclude(verification_status=VerificationStatus.REJECTED).prefetch_related(
            Prefetch("contributions", queryset=Contribution.objects.select_related("person")),
            Prefetch(
                "editions",
                queryset=Edition.objects.select_related("publisher", "series", "source").prefetch_related(
                    Prefetch(
                        "access_links", queryset=AccessLink.objects.select_related("source").filter(is_active=True)
                    )
                ),
            ),
            "subjects",
        ),
        slug=slug,
    )
    Work.objects.filter(pk=work.pk).update(view_count=F("view_count") + 1)

    editions = list(work.editions.all())
    editions.sort(key=lambda e: (e.language != "ar", -(e.publication_year or 0)))
    contributions = list(work.contributions.all())

    translations = WorkTranslation.objects.filter(verification_status=VerificationStatus.VERIFIED).select_related(
        "original", "translated", "translator"
    )

    subject_ids = [s.id for s in work.subjects.all()]
    related = (
        _work_list_qs(
            Work.objects.filter(subjects__id__in=subject_ids)
            .exclude(pk=work.pk)
            .exclude(verification_status=VerificationStatus.REJECTED)
            .distinct()
            .order_by("-created_at")
        )[:6]
        if subject_ids
        else []
    )
    author_ids = [c.person_id for c in contributions if c.role == Contribution.Role.AUTHOR]
    same_author = (
        _work_list_qs(Work.objects.filter(contributions__person_id__in=author_ids).exclude(pk=work.pk).distinct())[:6]
        if author_ids
        else []
    )

    is_saved = False
    user_rating = None
    if request.user.is_authenticated:
        from library.models import ReadingEntry, SavedWork

        is_saved = SavedWork.objects.filter(user=request.user, work=work).exists()
        user_rating = work.ratings.filter(user=request.user).first()
        entry, created = ReadingEntry.objects.get_or_create(user=request.user, work=work)
        if not created:
            ReadingEntry.objects.filter(pk=entry.pk).update(open_count=F("open_count") + 1)
            entry.save(update_fields=["last_opened_at"])

    ratings = work.ratings.select_related("user").order_by("-updated_at")[:20]

    context = {
        "work": work,
        "editions": editions,
        "authors": [c for c in contributions if c.role == Contribution.Role.AUTHOR],
        "other_contributors": [c for c in contributions if c.role != Contribution.Role.AUTHOR],
        "translations_of": translations.filter(original=work),
        "translated_from": translations.filter(translated=work),
        "related": related,
        "same_author": same_author,
        "is_saved": is_saved,
        "user_rating": user_rating,
        "ratings": ratings,
        "rating_count": work.ratings.count(),
    }
    return render(request, "catalog/work_detail.html", context)


def hosted_file(request, link_id):
    """يخدم ملفًا مستضافًا فقط إذا كانت حقوقه موثقة وتسمح بالتوزيع."""
    link = get_object_or_404(AccessLink.objects.select_related("edition__work"), pk=link_id)
    if not link.can_serve_hosted_file:
        raise Http404
    try:
        handle = link.hosted_file.open("rb")
    except FileNotFoundError as exc:
        raise Http404 from exc
    filename = f"{link.edition.work.slug}.pdf"
    return FileResponse(handle, as_attachment=False, filename=filename, content_type="application/pdf")


def topics(request):
    roots = (
        Subject.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .annotate(n=Count("works", distinct=True))
        .order_by("sort_order")
    )
    return render(request, "catalog/topics.html", {"roots": roots})


def topic_detail(request, slug):
    subject = get_object_or_404(Subject, slug=slug, is_active=True)
    results = search_works(subject=subject)
    page = Paginator(_work_list_qs(results.order_by("-created_at")), PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "subject": subject,
        "ancestors": subject.ancestors(),
        "children": subject.children.filter(is_active=True).annotate(n=Count("works", distinct=True)),
        "page_obj": page,
        "total": page.paginator.count,
    }
    return render(request, "catalog/topic_detail.html", context)


def people(request):
    qs = Person.objects.annotate(n=Count("contributions__work", distinct=True)).filter(n__gt=0)
    query = request.GET.get("q", "").strip()
    if query:
        for token in normalize_key(query).split():
            qs = qs.filter(normalized_name__icontains=token)
    page = Paginator(qs.order_by("-is_featured", "name"), 30).get_page(request.GET.get("page"))
    return render(request, "catalog/people.html", {"page_obj": page, "query": query, "total": page.paginator.count})


def person_detail(request, slug):
    person = get_object_or_404(Person, slug=slug)
    works = _work_list_qs(
        Work.objects.filter(contributions__person=person)
        .exclude(verification_status=VerificationStatus.REJECTED)
        .distinct()
        .order_by("-created_at")
    )
    roles = sorted({c.get_role_display() for c in person.contributions.all()})
    return render(request, "catalog/person_detail.html", {"person": person, "works": works, "roles": roles})


# ---------------------------------------------------------------- legacy URLs


def legacy_category(request, slug):
    subject = Subject.objects.filter(slug=slug).first()
    if subject is None:
        raise Http404
    return redirect("topic_detail", slug=subject.slug, permanent=True)


def legacy_categories(request):
    return redirect("topics", permanent=True)


def legacy_author(request, author_id):
    """روابط /author/<id>/ القديمة: نطابق الاسم مع Person."""
    author = get_object_or_404(LegacyAuthor, pk=author_id)
    person = Person.objects.filter(normalized_name=normalize_key(author.name)).first()
    if person is None:
        raise Http404
    return redirect("person_detail", slug=person.slug, permanent=True)
