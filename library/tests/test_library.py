import pytest
from django.apps import apps
from django.urls import reverse

from books.models import Book, Bookmark, Category, ReadingHistory, Review
from catalog.legacy import import_legacy_books
from library.legacy import import_legacy_user_data
from library.models import Rating, ReadingEntry, SavedWork


@pytest.mark.django_db
def test_save_toggle_json(client, user, work):
    client.force_login(user)
    url = reverse("toggle_save", args=[work.id])
    assert client.post(url, HTTP_ACCEPT="application/json").json() == {"saved": True}
    assert client.post(url, HTTP_ACCEPT="application/json").json() == {"saved": False}
    assert not SavedWork.objects.exists()


@pytest.mark.django_db
def test_save_requires_login_and_post(client, user, work):
    url = reverse("toggle_save", args=[work.id])
    assert client.post(url).status_code == 302  # إلى صفحة الدخول
    client.force_login(user)
    assert client.get(url).status_code == 405


@pytest.mark.django_db
def test_rating_range_enforced(client, user, work):
    client.force_login(user)
    client.post(reverse("rate_work", args=[work.id]), {"score": 9})
    assert not Rating.objects.exists()
    client.post(reverse("rate_work", args=[work.id]), {"score": 4, "comment": "مفيد"})
    client.post(reverse("rate_work", args=[work.id]), {"score": 5})
    rating = Rating.objects.get()
    assert rating.score == 5


@pytest.mark.django_db
def test_opening_detail_records_history(client, user, work):
    client.force_login(user)
    client.get(work.get_absolute_url())
    client.get(work.get_absolute_url())
    entry = ReadingEntry.objects.get(user=user, work=work)
    assert entry.open_count == 2


@pytest.mark.django_db
def test_my_library_lists_saved(client, user, work):
    client.force_login(user)
    SavedWork.objects.create(user=user, work=work)
    resp = client.get(reverse("my_library"))
    assert resp.status_code == 200
    assert [w.id for w in resp.context["saved"]] == [work.id]


@pytest.mark.django_db
def test_legacy_user_data_is_migrated(user):
    category = Category.objects.create(name="programming")
    book = Book.objects.create(title="Legacy", category=category)
    Bookmark.objects.create(user=user, book=book)
    Review.objects.create(user=user, book=book, rating=4, comment="جيد")
    ReadingHistory.objects.create(user=user, book=book)

    import_legacy_books(apps)
    counts = import_legacy_user_data(apps)
    assert counts == {"saved": 1, "ratings": 1, "history": 1}
    assert import_legacy_user_data(apps) == {"saved": 0, "ratings": 0, "history": 0}
    assert Rating.objects.get(user=user).comment == "جيد"
