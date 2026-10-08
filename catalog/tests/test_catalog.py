import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Author, Book, Category
from catalog.identifiers import (
    is_valid_isbn10,
    is_valid_isbn13,
    isbn10_to_isbn13,
    normalize_doi,
    validate_orcid,
)
from catalog.legacy import import_legacy_books
from catalog.models import (
    AccessLink,
    AccessStatus,
    Contribution,
    Edition,
    Person,
    RightsStatus,
    Subject,
    VerificationStatus,
    Work,
    WorkTranslation,
)
from catalog.quality import quality_report
from sources.models import Source

# ---------------------------------------------------------------- identifiers


def test_isbn_validation():
    # Clean Code (ISBN حقيقي)
    assert is_valid_isbn13("978-0-13-235088-4")
    assert is_valid_isbn10("0-13-235088-2")
    assert not is_valid_isbn13("978-0-13-235088-5")
    assert not is_valid_isbn10("0132350881")
    assert is_valid_isbn10("080442957X")


def test_isbn10_to_13():
    assert isbn10_to_isbn13("0132350882") == "9780132350884"
    assert isbn10_to_isbn13("bad") is None


def test_doi_normalization():
    assert normalize_doi("https://doi.org/10.1000/XYZ123") == "10.1000/xyz123"
    assert normalize_doi("doi:10.48550/arXiv.1706.03762") == "10.48550/arxiv.1706.03762"
    assert normalize_doi("not a doi") == ""


def test_orcid_checksum():
    validate_orcid("0000-0002-1825-0097")  # مثال ORCID الرسمي
    with pytest.raises(ValidationError):
        validate_orcid("0000-0002-1825-0098")


# ---------------------------------------------------------------- taxonomy


@pytest.mark.django_db
def test_taxonomy_is_seeded_as_tree():
    dl = Subject.objects.get(slug="deep-learning")
    assert [s.slug for s in dl.ancestors()] == ["computer-science", "artificial-intelligence", "machine-learning"]
    assert Subject.objects.get(slug="organic-chemistry").parent.slug == "chemistry"


@pytest.mark.django_db
def test_manual_source_exists():
    assert Source.objects.filter(slug="manual", allows_rehosting=False).exists()


# ---------------------------------------------------------------- works & editions


@pytest.fixture
def work(db):
    return Work.objects.create(title="الذكاء الإصطناعي: مقدمة")


def test_work_normalized_title_and_slug(work):
    assert work.normalized_title == "ذكاء اصطناعي مقدمه"
    assert work.slug == "الذكاء-الإصطناعي-مقدمة"


@pytest.mark.django_db
def test_edition_cleans_identifiers(work):
    edition = Edition.objects.create(work=work, isbn13="978-0-13-235088-4", doi="https://doi.org/10.1000/ABC")
    assert edition.isbn13 == "9780132350884"
    assert edition.doi == "10.1000/abc"


@pytest.mark.django_db
def test_preferred_edition_is_arabic_first(work):
    Edition.objects.create(work=work, language="en", publication_year=2020)
    arabic = Edition.objects.create(work=work, language="ar", publication_year=2010)
    assert work.preferred_edition() == arabic


@pytest.mark.django_db
def test_same_source_record_cannot_be_imported_twice(work):
    source = Source.objects.get(slug="manual")
    Edition.objects.create(work=work, source=source, source_record_id="OL1M")
    with pytest.raises(IntegrityError), transaction.atomic():
        Edition.objects.create(work=work, source=source, source_record_id="OL1M")


@pytest.mark.django_db
def test_translation_cannot_point_to_itself(work):
    with pytest.raises(IntegrityError), transaction.atomic():
        WorkTranslation.objects.create(original=work, translated=work, language="ar")


# ---------------------------------------------------------------- access rules


@pytest.fixture
def edition(work):
    return Edition.objects.create(work=work, language="en")


@pytest.mark.django_db
def test_no_links_means_metadata_only(edition):
    assert edition.access_summary == AccessStatus.METADATA_ONLY


@pytest.mark.django_db
def test_unverified_open_access_is_not_free(edition):
    link = AccessLink.objects.create(
        edition=edition, link_type="DOWNLOAD", url="https://example.org/a.pdf", access_status=AccessStatus.OPEN_ACCESS
    )
    assert not link.allows_free_access
    link.verification_status = VerificationStatus.VERIFIED
    assert link.allows_free_access


@pytest.mark.django_db
def test_unknown_status_is_never_trusted(edition):
    link = AccessLink.objects.create(
        edition=edition,
        link_type="DOWNLOAD",
        url="https://example.org/a.pdf",
        access_status=AccessStatus.UNKNOWN,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert not link.is_trusted
    assert not link.allows_free_access


@pytest.mark.django_db
def test_hosted_file_needs_verified_free_rights(edition):
    link = AccessLink.objects.create(
        edition=edition,
        link_type="DOWNLOAD",
        hosted_file="books/pdfs/x.pdf",
        access_status=AccessStatus.PUBLIC_DOMAIN,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert not link.can_serve_hosted_file
    link.rights_status = RightsStatus.VERIFIED_FREE
    assert link.can_serve_hosted_file


@pytest.mark.django_db
def test_paid_status_is_shown_but_not_free(edition):
    AccessLink.objects.create(
        edition=edition,
        link_type="PURCHASE",
        url="https://publisher.example/buy",
        access_status=AccessStatus.PAID,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert edition.access_summary == AccessStatus.PAID


@pytest.mark.django_db
def test_access_link_requires_url_or_file(edition):
    with pytest.raises(IntegrityError), transaction.atomic():
        AccessLink.objects.create(edition=edition, link_type="DOWNLOAD")


# ---------------------------------------------------------------- quality


@pytest.mark.django_db
def test_quality_report_lists_missing(work):
    score, missing = quality_report(work)
    assert score == 10  # العنوان فقط
    assert "مؤلف واحد على الأقل" in missing


# ---------------------------------------------------------------- legacy import


@pytest.mark.django_db
def test_legacy_import_maps_without_inventing():
    category = Category.objects.create(name="Organic Chemistry")
    author = Author.objects.create(name="Francis A. Carey", bio="bio", email="private@example.com")
    book = Book.objects.create(
        title="Advanced Organic Chemistry",
        author=author,
        category=category,
        published_year=2007,
        pages=1347,
        language="English",
        is_free=True,
        price=0,
        pdf_file="books/pdfs/legacy.pdf",
    )

    assert import_legacy_books(apps) == 1
    assert import_legacy_books(apps) == 0  # idempotent

    work = Work.objects.get(legacy_book=book)
    assert work.slug == book.slug
    assert work.original_language == "en"
    assert [s.slug for s in work.subjects.all()] == ["organic-chemistry"]

    contribution = Contribution.objects.get(work=work)
    assert contribution.person.name == "Francis A. Carey"
    assert not hasattr(contribution.person, "email")

    edition = work.editions.get()
    assert edition.publication_year == 2007
    assert edition.page_count == 1347

    # is_free=True في النظام القديم لا يتحول إلى "مجاني"
    link = edition.access_links.get()
    assert link.access_status == AccessStatus.UNKNOWN
    assert link.rights_status == RightsStatus.UNKNOWN
    assert not link.allows_free_access
    assert not link.can_serve_hosted_file


@pytest.mark.django_db
def test_legacy_author_name_only_becomes_person():
    category = Category.objects.create(name="programming")
    Book.objects.create(title="كتاب", author_name="مؤلف نصي", category=category)
    import_legacy_books(apps)
    assert Person.objects.filter(name="مؤلف نصي").exists()
    # التصنيف القديم "programming" يطابق "Programming" في التصنيف الجديد
    assert Work.objects.get(title="كتاب").subjects.get().slug == "programming"
