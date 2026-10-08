import pytest
from django.contrib.auth.models import User

from books.models import Author, Book, Category


@pytest.fixture
def category(db):
    return Category.objects.create(name="البرمجة")


@pytest.fixture
def author(db):
    return Author.objects.create(name="Jim McGaw")


@pytest.fixture
def book(db, category, author):
    return Book.objects.create(title="Beginning Django E-Commerce", category=category, author=author)


@pytest.fixture
def user(db):
    return User.objects.create_user("reader", "reader@example.com", "S3cure-pass-123")


@pytest.fixture
def staff(db):
    return User.objects.create_user("staff", "staff@example.com", "S3cure-pass-123", is_staff=True)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser("root", "root@example.com", "S3cure-pass-123")
