"""درجة جودة البيانات (0-100) لعمل وطبعاته. تظهر للإدارة فقط.

كل بند له وزن؛ الدرجة = مجموع أوزان البنود المتحققة. القائمة تُعاد مع الدرجة
لتعرف الإدارة ما الناقص.
"""

from .models import AccessStatus, Contribution, VerificationStatus

CHECKS = [
    # (المفتاح، الوزن، الوصف)
    ("title", 10, "عنوان"),
    ("description", 10, "وصف (50 حرفًا على الأقل)"),
    ("authors", 15, "مؤلف واحد على الأقل"),
    ("subjects", 10, "موضوع واحد على الأقل"),
    ("language", 5, "لغة الطبعة"),
    ("year", 5, "سنة النشر"),
    ("publisher", 5, "الناشر"),
    ("identifier", 15, "معرّف موثوق (ISBN صالح أو DOI)"),
    ("source", 10, "مصدر معروف"),
    ("access", 5, "حالة وصول معروفة"),
    ("verified", 10, "تم التحقق"),
]


def quality_report(work):
    editions = list(work.editions.all())
    authors = [c for c in work.contributions.all() if c.role == Contribution.Role.AUTHOR]
    links = [link for e in editions for link in e.access_links.all()]
    passed = {
        "title": bool(work.title.strip()),
        "description": len(work.description.strip()) >= 50,
        "authors": bool(authors),
        "subjects": bool(list(work.subjects.all())),
        "language": any(e.language for e in editions),
        "year": any(e.publication_year for e in editions) or bool(work.first_publication_year),
        "publisher": any(e.publisher_id for e in editions),
        "identifier": bool(work.doi) or any(e.isbn13 or e.isbn10 or e.doi for e in editions),
        "source": any(e.source_id for e in editions),
        "access": any(link.access_status != AccessStatus.UNKNOWN for link in links),
        "verified": work.verification_status == VerificationStatus.VERIFIED,
    }
    score = sum(weight for key, weight, _ in CHECKS if passed[key])
    missing = [label for key, _, label in CHECKS if not passed[key]]
    return score, missing


def quality_score(work):
    return quality_report(work)[0]
