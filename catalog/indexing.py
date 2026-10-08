"""بناء فهرس البحث لكل عمل.

search_document: نص مطبّع (core.arabic.normalize_key) يجمع:
  العنوان، العنوان الفرعي، العنوان الأصلي، أسماء المساهمين، الموضوعات (عربي/إنجليزي) وآباءها،
  الكلمات المفتاحية، الناشرين، وأول جزء من الوصف.
search_vector (PostgreSQL فقط): tsvector بإعداد 'simple' على النص المطبّع،
  العنوان بوزن A والباقي بوزن B.

التحديث تلقائي عبر الإشارات (catalog.signals)، ويمكن تعليقه أثناء الاستيراد الجماعي
بـ suspended_indexing() ثم استدعاء index_works() مرة واحدة.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from django.contrib.postgres.search import SearchVector
from django.db import connection

from core.arabic import normalize_key

DESCRIPTION_CHARS = 1500
_suspended = ContextVar("catalog_indexing_suspended", default=False)


@contextmanager
def suspended_indexing():
    token = _suspended.set(True)
    try:
        yield
    finally:
        _suspended.reset(token)


def indexing_suspended():
    return _suspended.get()


def build_document(work):
    parts = [work.title, work.subtitle, work.original_title]
    for contribution in work.contributions.all():
        person = contribution.person
        parts += [person.name, person.native_name]
    for subject in work.subjects.all():
        parts += [subject.name, subject.name_en]
        for ancestor in subject.ancestors():
            parts += [ancestor.name, ancestor.name_en]
    parts += [str(k) for k in (work.keywords or [])]
    for edition in work.editions.all():
        if edition.publisher_id:
            parts.append(edition.publisher.name)
        parts += [edition.title, edition.isbn13, edition.isbn10]
    parts.append((work.description or "")[:DESCRIPTION_CHARS])
    return normalize_key(" ".join(p for p in parts if p))


def index_works(work_ids):
    """يحدّث فهرس البحث لمجموعة أعمال (بـ update، دون إطلاق إشارات الحفظ)."""
    from .models import Work

    ids = list(work_ids)
    if not ids:
        return 0
    works = Work.objects.filter(id__in=ids).prefetch_related(
        "contributions__person", "subjects__parent__parent__parent", "editions__publisher"
    )
    for work in works:
        Work.objects.filter(pk=work.pk).update(search_document=build_document(work))
    if connection.vendor == "postgresql":
        Work.objects.filter(id__in=ids).update(
            search_vector=SearchVector("normalized_title", weight="A", config="simple")
            + SearchVector("search_document", weight="B", config="simple")
        )
    return len(ids)


def index_all(batch_size=500, log=None):
    from .models import Work

    ids = list(Work.objects.order_by("id").values_list("id", flat=True))
    for start in range(0, len(ids), batch_size):
        index_works(ids[start : start + batch_size])
        if log:
            log(f"[index] {min(start + batch_size, len(ids))}/{len(ids)}")
    return len(ids)
