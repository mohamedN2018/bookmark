import pytest
from django.contrib.auth.models import User

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
)


@pytest.fixture
def user(db):
    return User.objects.create_user("reader", "reader@example.com", "S3cure-pass-123")


@pytest.fixture
def staff(db):
    return User.objects.create_user("staff", "staff@example.com", "S3cure-pass-123", is_staff=True)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser("root", "root@example.com", "S3cure-pass-123")


@pytest.fixture
def person(db):
    return Person.objects.create(name="Robert C. Martin")


@pytest.fixture
def work(db, person):
    work = Work.objects.create(title="الذكاء الاصطناعي للمبتدئين", description="وصف " * 20)
    work.subjects.add(Subject.objects.get(slug="artificial-intelligence"))
    Contribution.objects.create(work=work, person=person, role=Contribution.Role.AUTHOR)
    return work


@pytest.fixture
def edition(work):
    return Edition.objects.create(work=work, language="ar", publication_year=2020, isbn13="9780132350884")


@pytest.fixture
def verified_pd_link(edition):
    return AccessLink.objects.create(
        edition=edition,
        link_type=AccessLink.LinkType.DOWNLOAD,
        hosted_file="books/pdfs/pd.pdf",
        access_status=AccessStatus.PUBLIC_DOMAIN,
        rights_status=RightsStatus.VERIFIED_FREE,
        verification_status=VerificationStatus.VERIFIED,
        license="Public Domain",
    )
