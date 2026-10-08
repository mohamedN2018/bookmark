from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from books.models import Book, ReadingHistory

# عبارات ممنوعة: مزاعم حجم/ريادة غير مثبتة بالبيانات، والهوية القديمة
BANNED_PHRASES = [
    "آلاف",
    "مليون",
    "الأولى في العالم العربي",
    "الرائدة",
    "أكبر مكتبة",
    "50K+",
    "100K+",
    "500K+",
    "10,000+",
    "مكتبة الكتب",
    "مكتبة مصر الرقمية",
    "Lorem",
    "dicebear",
]


def test_templates_contain_no_fake_claims():
    offenders = []
    for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for phrase in BANNED_PHRASES:
            if phrase in text:
                offenders.append(f"{path.name}: {phrase}")
    assert offenders == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["home", "book_list", "categories_list", "all_authors", "login", "register", "privacy"],
)
def test_public_pages_render(client, url_name, book):
    resp = client.get(reverse(url_name))
    assert resp.status_code == 200
    assert "المكتبة السرية" in resp.content.decode()


@pytest.mark.django_db
def test_home_shows_real_counts(client, book):
    resp = client.get(reverse("home"))
    assert resp.context["count_book"] == 1
    assert resp.context["count_author"] == 1
    assert resp.context["count_book_cat"] == 1


@pytest.mark.django_db
def test_book_detail_has_no_dead_download_or_buy_button(client, book):
    text = client.get(book.get_absolute_url()).content.decode()
    assert "تحميل الكتاب" not in text
    assert "شراء الآن" not in text
    assert "نوع الوصول" in text


@pytest.mark.django_db
def test_book_detail_increments_views_and_keeps_progress(client, user, book):
    ReadingHistory.objects.create(user=user, book=book, progress=40)
    client.force_login(user)
    client.get(book.get_absolute_url())
    client.get(book.get_absolute_url())
    book.refresh_from_db()
    assert book.views == 2
    assert ReadingHistory.objects.get(user=user, book=book).progress == 40


@pytest.mark.django_db
def test_search_suggest_returns_real_results(client, book):
    data = client.get(reverse("search_suggest"), {"q": "Django"}).json()
    assert data["results"] == [{"title": book.title, "author": "Jim McGaw", "url": book.get_absolute_url()}]
    assert client.get(reverse("search_suggest"), {"q": "x"}).json() == {"results": []}


@pytest.mark.django_db
def test_slug_collision_gets_suffix(category):
    a = Book.objects.create(title="Clean Code", category=category)
    b = Book.objects.create(title="Clean Code", category=category)
    assert a.slug == "clean-code"
    assert b.slug == "clean-code-2"


@pytest.mark.django_db
def test_dashboard_chart_uses_real_monthly_stats(client, staff, book):
    client.force_login(staff)
    resp = client.get(reverse("dashboard"))
    stats = resp.context["monthly_stats"]
    assert len(stats) == 6
    assert stats[-1]["books"] == 1
    assert "65, 59, 80" not in resp.content.decode()


@pytest.mark.django_db
def test_arabic_slug_urls_work(client, category):
    book = Book.objects.create(title="البرمجة بلغة بايثون", category=category)
    assert book.slug == "البرمجة-بلغة-بايثون"
    assert client.get(book.get_absolute_url()).status_code == 200
    assert client.get(category.get_absolute_url()).status_code == 200
