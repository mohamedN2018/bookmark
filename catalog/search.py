"""بحث الفهرس.

المرحلة الحالية: مطابقة على النصوص المطبّعة (core.arabic.normalize_key) بحيث
"الذكاء الإصطناعي" تجد "ذكاء اصطناعي". كل كلمة في الاستعلام يجب أن تظهر في
العنوان أو أسماء المساهمين أو الموضوعات أو الكلمات المفتاحية.
ISBN و DOI يُطابقان مباشرة.
المرحلة 4 تضيف الترتيب حسب الصلة، تحمّل الأخطاء الإملائية، والمرادفات.
"""

from django.db.models import Q

from core.arabic import normalize_key

from .identifiers import clean_isbn, is_valid_isbn10, is_valid_isbn13, normalize_doi
from .models import FREE_ACCESS_STATUSES, AccessStatus, Subject, VerificationStatus, Work

MAX_QUERY_LENGTH = 200


def _identifier_filter(query):
    isbn = clean_isbn(query)
    if is_valid_isbn13(isbn):
        return Q(editions__isbn13=isbn)
    if is_valid_isbn10(isbn):
        return Q(editions__isbn10=isbn)
    doi = normalize_doi(query)
    if doi:
        return Q(doi=doi) | Q(editions__doi=doi)
    return None


def _token_filter(token):
    return (
        Q(normalized_title__icontains=token)
        | Q(contributions__person__normalized_name__icontains=token)
        | Q(subjects__normalized_name__icontains=token)
        | Q(editions__publisher__normalized_name__icontains=token)
    )


def free_access_q(prefix=""):
    """أعمال لها رابط وصول مجاني قانوني مُتحقق منه."""
    return Q(
        **{
            f"{prefix}editions__access_links__access_status__in": list(FREE_ACCESS_STATUSES),
            f"{prefix}editions__access_links__verification_status": VerificationStatus.VERIFIED,
            f"{prefix}editions__access_links__is_active": True,
            f"{prefix}editions__access_links__is_broken": False,
        }
    )


def search_works(query="", *, subject=None, language="", content_type="", access=""):
    qs = Work.objects.exclude(verification_status=VerificationStatus.REJECTED)
    query = (query or "").strip()[:MAX_QUERY_LENGTH]

    if query:
        identifier = _identifier_filter(query)
        if identifier is not None:
            qs = qs.filter(identifier)
        else:
            tokens = normalize_key(query).split()
            for token in tokens:
                ids = Work.objects.filter(_token_filter(token)).values("id")
                qs = qs.filter(id__in=ids)

    if subject is not None:
        subject_ids = [subject.id, *_descendant_ids(subject)]
        qs = qs.filter(subjects__id__in=subject_ids)
    if language:
        qs = qs.filter(Q(original_language=language) | Q(editions__language=language))
    if content_type:
        qs = qs.filter(content_type=content_type)
    if access == "free":
        qs = qs.filter(free_access_q())
    elif access == "paid":
        qs = qs.filter(editions__access_links__access_status=AccessStatus.PAID)
    elif access == "metadata":
        qs = qs.exclude(editions__access_links__is_active=True)

    return qs.distinct()


def _descendant_ids(subject):
    ids, frontier = [], [subject.id]
    while frontier:
        children = list(Subject.objects.filter(parent_id__in=frontier).values_list("id", flat=True))
        children = [c for c in children if c not in ids]
        ids.extend(children)
        frontier = children
    return ids
