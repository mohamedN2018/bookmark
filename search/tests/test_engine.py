import pytest
from django.db import connection
from django.urls import reverse

from catalog.models import (
    AccessLink,
    AccessStatus,
    Contribution,
    Edition,
    Person,
    Subject,
    VerificationStatus,
    Work,
)
from search.engine import expand_query, search
from search.models import SearchLog, SearchSettings, Synonym

postgres_only = pytest.mark.skipif("connection.vendor != 'postgresql'", reason="PostgreSQL فقط")


def ids(result):
    return [w.id for w in result.queryset]


@pytest.fixture
def library(db):
    ai = Work.objects.create(title="مقدمة في الذكاء الاصطناعي", description="كتاب تمهيدي")
    ai.subjects.add(Subject.objects.get(slug="artificial-intelligence"))
    Edition.objects.create(work=ai, language="ar", publication_year=2022, isbn13="9780132350884")

    ml = Work.objects.create(title="Machine Learning Foundations", original_language="en")
    ml.subjects.add(Subject.objects.get(slug="machine-learning"))
    Edition.objects.create(work=ml, language="en", publication_year=2019)

    bio = Work.objects.create(title="On the Origin of Species", original_language="en", description="evolution")
    bio.subjects.add(Subject.objects.get(slug="biology"))
    darwin = Person.objects.create(name="Charles Darwin")
    Contribution.objects.create(work=bio, person=darwin)
    edition = Edition.objects.create(work=bio, language="en", publication_year=1859)
    AccessLink.objects.create(
        edition=edition,
        link_type="READ_ONLINE",
        url="https://www.gutenberg.org/ebooks/2009",
        access_status=AccessStatus.PUBLIC_DOMAIN,
        verification_status=VerificationStatus.VERIFIED,
    )
    return {"ai": ai, "ml": ml, "bio": bio}


# ---------------------------------------------------------------- matching


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["الذكاء الإصطناعي", "ذكاء اصطناعي", "الذَّكاء الاصطناعيّ", "مقدمه"])
def test_arabic_normalization(library, query):
    assert library["ai"].id in ids(search(query))


@pytest.mark.django_db
def test_synonyms_cross_language(library):
    # "AI" يجد الكتاب العربي عن الذكاء الاصطناعي
    assert library["ai"].id in ids(search("AI"))
    # "تعلم الآلة" يجد الكتاب الإنجليزي
    assert library["ml"].id in ids(search("تعلم الآلة"))


@pytest.mark.django_db
def test_author_and_subject_are_searchable(library):
    assert ids(search("Darwin")) == [library["bio"].id]
    assert library["bio"].id in ids(search("الأحياء"))


@pytest.mark.django_db
def test_prefix_for_autocomplete(library):
    assert library["ml"].id in ids(search("Machine Lear"))


@pytest.mark.django_db
def test_isbn_lookup(library):
    result = search("978-0-13-235088-4")
    assert result.identifier
    assert ids(result) == [library["ai"].id]


@pytest.mark.django_db
def test_no_match(library):
    assert ids(search("Quantum Field Theory")) == []


@postgres_only
@pytest.mark.django_db
def test_typo_tolerance(library):
    result = search("Machine Lerning Fundations")
    assert result.approximate
    assert library["ml"].id in ids(result)


# ---------------------------------------------------------------- ranking


@pytest.mark.django_db
def test_title_match_outranks_description_match(db):
    in_title = Work.objects.create(title="Evolution of Stars")
    in_desc = Work.objects.create(title="Astronomy Notes", description="a chapter on evolution")
    for work in (in_title, in_desc):
        work.subjects.add(Subject.objects.get(slug="astronomy"))
    assert ids(search("evolution"))[0] == in_title.id


@pytest.mark.django_db
def test_free_access_bonus_affects_order(db):
    plain = Work.objects.create(title="Organic Chemistry Basics")
    free = Work.objects.create(title="Organic Chemistry Basics")
    edition = Edition.objects.create(work=free)
    AccessLink.objects.create(
        edition=edition,
        link_type="DOWNLOAD",
        url="https://example.org/a.pdf",
        access_status=AccessStatus.OPEN_ACCESS,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert ids(search("organic chemistry"))[:2] == [free.id, plain.id]


@pytest.mark.django_db
def test_weights_are_configurable(db):
    english = Work.objects.create(title="Robotics", original_language="en")
    arabic = Work.objects.create(title="Robotics", original_language="ar")
    settings = SearchSettings.current()
    settings.arabic_bonus = 5
    settings.save()
    assert ids(search("robotics"))[0] == arabic.id
    settings.arabic_bonus = -5
    settings.save()
    assert ids(search("robotics"))[0] == english.id


def test_expand_query_uses_synonyms(db):
    Synonym.objects.create(terms="حاسوب\ncomputer")
    assert set(expand_query("حاسوب كمي")) == {"حاسوب كمي", "computer كمي"}


# ---------------------------------------------------------------- filters & ordering


@pytest.mark.django_db
def test_subject_filter_includes_descendants(library):
    root = Subject.objects.get(slug="computer-science")
    assert set(ids(search(subject=root))) == {library["ai"].id, library["ml"].id}


@pytest.mark.django_db
def test_free_filter(library):
    assert ids(search(access="free")) == [library["bio"].id]


@pytest.mark.django_db
def test_order_by_publication_year(library):
    assert ids(search(order="year")) == [library["ai"].id, library["ml"].id, library["bio"].id]


# ---------------------------------------------------------------- indexing


@pytest.mark.django_db
def test_index_updates_when_author_added(db):
    work = Work.objects.create(title="Linear Algebra")
    assert ids(search("Strang")) == []
    Contribution.objects.create(work=work, person=Person.objects.create(name="Gilbert Strang"))
    assert ids(search("Strang")) == [work.id]


@pytest.mark.django_db
def test_search_vector_is_built_on_postgres(library):
    library["ai"].refresh_from_db()
    assert "ذكاء" in library["ai"].search_document
    if connection.vendor == "postgresql":
        assert library["ai"].search_vector


# ---------------------------------------------------------------- analytics


@pytest.mark.django_db
def test_search_page_logs_anonymously(client, library):
    client.get(reverse("search"), {"q": "Quantum Field Theory"}, HTTP_USER_AGENT="Mozilla/5.0")
    client.get(reverse("search"), {"q": "Darwin"}, HTTP_USER_AGENT="Mozilla/5.0")
    logs = {log.query: log.results for log in SearchLog.objects.all()}
    assert logs == {"Quantum Field Theory": 0, "Darwin": 1}
    field_names = {f.name for f in SearchLog._meta.fields}
    assert not field_names & {"user", "ip", "ip_address", "session"}


@pytest.mark.django_db
def test_bots_and_suggest_are_not_logged(client, library):
    client.get(reverse("search"), {"q": "Darwin"}, HTTP_USER_AGENT="Googlebot/2.1")
    client.get(reverse("search_suggest"), {"q": "Darwin"}, HTTP_USER_AGENT="Mozilla/5.0")
    assert not SearchLog.objects.exists()


@pytest.mark.django_db
def test_insights_admin_page(client, superuser, library):
    SearchLog.objects.create(query="quantum", normalized_query="quantum", results=0)
    client.force_login(superuser)
    resp = client.get(reverse("admin:search_insights"))
    assert resp.status_code == 200
    assert "quantum" in resp.content.decode()


@pytest.mark.django_db
def test_popular_searches_on_home(client, library):
    for _ in range(2):
        SearchLog.objects.create(query="Darwin", normalized_query="darwin", results=1)
    assert "Darwin" in client.get("/").content.decode()


@postgres_only
@pytest.mark.django_db
def test_typo_inside_long_title(db):
    work = Work.objects.create(title="Atoms in Agriculture: Applications of Nuclear Science")
    result = search("agriculure")
    assert result.approximate
    assert ids(result) == [work.id]
