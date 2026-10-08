from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse

from books.models import Author as LegacyAuthor
from catalog.models import AccessLink, AccessStatus, Person, RightsStatus, VerificationStatus

# عبارات ممنوعة: مزاعم حجم/ريادة غير مثبتة، والهوية القديمة، ومحتوى وهمي
BANNED_PHRASES = [
    "آلاف",
    "مليون",
    "الأولى في العالم العربي",
    "الرائدة",
    "أكبر مكتبة",
    "50K+",
    "100K+",
    "10,000+",
    "مكتبة الكتب",
    "مكتبة مصر الرقمية",
    "Lorem",
    "dicebear",
    "cdn.tailwindcss.com",
]


def test_templates_contain_no_fake_claims():
    offenders = []
    for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        offenders += [f"{path.name}: {p}" for p in BANNED_PHRASES if p in text]
    assert offenders == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    ["/", "/books/", "/topics/", "/topics/artificial-intelligence/", "/authors/", "/login/", "/register/", "/privacy/"],
)
def test_public_pages_render(client, url, edition):
    resp = client.get(url)
    assert resp.status_code == 200
    assert "المكتبة السرية" in resp.content.decode()


@pytest.mark.django_db
def test_home_counts_are_real(client, edition):
    stats = client.get("/").context["stats"]
    assert stats["works"] == 1
    assert stats["people"] == 1
    assert stats["free"] == 0


# ---------------------------------------------------------------- search


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query", ["الذكاء الإصطناعي", "ذكاء اصطناعي", "الذَّكاء", "Martin", "9780132350884", "978-0-13-235088-4"]
)
def test_search_finds_with_normalization_and_identifiers(client, edition, query):
    resp = client.get(reverse("search"), {"q": query})
    assert resp.context["total"] == 1


@pytest.mark.django_db
def test_search_by_subject_includes_descendants(client, edition):
    # العمل مصنّف في "الذكاء الاصطناعي"؛ البحث في الأب "علوم الحاسب" يجده
    resp = client.get(reverse("search"), {"subject": "computer-science"})
    assert resp.context["total"] == 1


@pytest.mark.django_db
def test_no_results_page_is_helpful(client, edition):
    resp = client.get(reverse("search"), {"q": "Quantum Field Theory"})
    text = resp.content.decode()
    assert resp.context["total"] == 0
    assert "لم نجد مصدرًا مناسبًا بعد" in text
    assert "openalex.org" in text
    assert "لا توجد نتائج" not in text


@pytest.mark.django_db
def test_free_filter_only_counts_verified_free(client, edition):
    AccessLink.objects.create(
        edition=edition, link_type="DOWNLOAD", url="https://example.org/x.pdf", access_status=AccessStatus.OPEN_ACCESS
    )
    assert client.get(reverse("search"), {"access": "free"}).context["total"] == 0


@pytest.mark.django_db
def test_suggest(client, edition, work):
    data = client.get(reverse("search_suggest"), {"q": "ذكاء"}).json()
    assert data["results"][0]["url"] == work.get_absolute_url()
    assert data["results"][0]["author"] == "Robert C. Martin"


# ---------------------------------------------------------------- detail & access rules


@pytest.mark.django_db
def test_detail_without_links_is_metadata_only(client, edition, work):
    text = client.get(work.get_absolute_url()).content.decode()
    assert "بياناته الوصفية فقط" in text
    assert ">تحميل<" not in text
    assert '"@type": "Book"' in text
    assert "9780132350884" in text


@pytest.mark.django_db
def test_unknown_hosted_file_is_not_offered_or_served(client, edition, work):
    link = AccessLink.objects.create(
        edition=edition, link_type="DOWNLOAD", hosted_file="books/pdfs/legacy.pdf", access_status=AccessStatus.UNKNOWN
    )
    text = client.get(work.get_absolute_url()).content.decode()
    assert reverse("hosted_file", args=[link.id]) not in text
    assert "قيد مراجعة الحقوق" in text
    assert client.get(reverse("hosted_file", args=[link.id])).status_code == 404


@pytest.mark.django_db
def test_verified_public_domain_file_is_downloadable(client, settings, tmp_path, verified_pd_link, work):
    settings.MEDIA_ROOT = tmp_path
    verified_pd_link.hosted_file.save("pd.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
    url = reverse("hosted_file", args=[verified_pd_link.id])
    assert url in client.get(work.get_absolute_url()).content.decode()
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert b"".join(resp.streaming_content).startswith(b"%PDF")


@pytest.mark.django_db
def test_verified_open_access_without_rights_links_out_but_not_hosted(client, edition, work):
    link = AccessLink.objects.create(
        edition=edition,
        link_type="READ_ONLINE",
        url="https://repository.example.org/item/1",
        access_status=AccessStatus.OPEN_ACCESS,
        verification_status=VerificationStatus.VERIFIED,
        license="CC BY 4.0",
    )
    text = client.get(work.get_absolute_url()).content.decode()
    assert "قراءة المصدر" in text
    assert "CC BY 4.0" in text
    assert link.url in text


@pytest.mark.django_db
def test_purchase_link_shown_as_purchase(client, edition, work):
    AccessLink.objects.create(
        edition=edition,
        link_type="PURCHASE",
        url="https://publisher.example/buy",
        access_status=AccessStatus.PAID,
        verification_status=VerificationStatus.VERIFIED,
    )
    text = client.get(work.get_absolute_url()).content.decode()
    assert "شراء الكتاب" in text
    assert ">تحميل<" not in text


@pytest.mark.django_db
def test_rights_not_verified_free_blocks_hosting(client, verified_pd_link):
    verified_pd_link.rights_status = RightsStatus.UNKNOWN
    verified_pd_link.save()
    assert client.get(reverse("hosted_file", args=[verified_pd_link.id])).status_code == 404


@pytest.mark.django_db
def test_view_count_increments(client, work):
    client.get(work.get_absolute_url())
    client.get(work.get_absolute_url())
    work.refresh_from_db()
    assert work.view_count == 2


# ---------------------------------------------------------------- legacy URLs


@pytest.mark.django_db
def test_legacy_category_redirects(client):
    resp = client.get("/category/programming/")
    assert resp.status_code == 301
    assert resp["Location"] == "/topics/programming/"


@pytest.mark.django_db
def test_legacy_author_redirects(client, person):
    author = LegacyAuthor.objects.create(name="Robert C. Martin")
    resp = client.get(f"/author/{author.id}/")
    assert resp.status_code == 301
    assert resp["Location"] == Person.objects.get().get_absolute_url()


@pytest.mark.django_db
def test_legacy_dashboard_redirects(client):
    assert client.get("/dashboard/")["Location"] == "/library/"
    assert client.get("/categories/")["Location"] == "/topics/"
