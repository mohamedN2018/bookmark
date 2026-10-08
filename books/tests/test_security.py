import pytest
from django.urls import reverse

from books.models import Book, Category


@pytest.mark.django_db
class TestLogin:
    def test_open_redirect_is_blocked(self, client, user):
        resp = client.post(
            reverse("login") + "?next=https://evil.example.com/",
            {"username": "reader", "password": "S3cure-pass-123"},
        )
        assert resp.status_code == 302
        assert resp["Location"] == reverse("dashboard")

    def test_internal_next_is_allowed(self, client, user):
        resp = client.post(
            reverse("login"),
            {"username": "reader", "password": "S3cure-pass-123", "next": "/books/"},
        )
        assert resp["Location"] == "/books/"

    def test_logout_requires_post(self, client, user):
        client.force_login(user)
        assert client.get(reverse("logout")).status_code == 405
        assert client.post(reverse("logout")).status_code == 302


@pytest.mark.django_db
class TestUserManagement:
    def test_staff_cannot_grant_staff(self, client, staff, user):
        client.force_login(staff)
        resp = client.post(reverse("toggle_staff_status", args=[user.id]))
        assert resp.status_code == 403
        user.refresh_from_db()
        assert not user.is_staff

    def test_superuser_can_grant_staff(self, client, superuser, user):
        client.force_login(superuser)
        resp = client.post(reverse("toggle_staff_status", args=[user.id]))
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_staff

    def test_staff_cannot_disable_superuser(self, client, staff, superuser):
        client.force_login(staff)
        resp = client.post(reverse("toggle_user_status", args=[superuser.id]))
        assert resp.status_code == 403
        superuser.refresh_from_db()
        assert superuser.is_active

    def test_cannot_disable_self(self, client, staff):
        client.force_login(staff)
        resp = client.post(reverse("toggle_user_status", args=[staff.id]))
        assert resp.status_code == 403

    def test_regular_user_cannot_toggle(self, client, user, staff):
        client.force_login(user)
        resp = client.post(reverse("toggle_user_status", args=[staff.id]))
        assert resp.status_code == 403

    def test_non_staff_cannot_delete_book(self, client, user, book):
        client.force_login(user)
        resp = client.post(reverse("delete_book", args=[book.id]))
        assert resp.status_code == 403
        assert Book.objects.filter(id=book.id).exists()


@pytest.mark.django_db
class TestProfile:
    def test_password_change_requires_current_password(self, client, user):
        client.force_login(user)
        client.post(
            reverse("profile"),
            {
                "email": "reader@example.com",
                "current_password": "wrong",
                "new_password": "An0ther-strong-pass",
                "new_password_confirm": "An0ther-strong-pass",
            },
        )
        user.refresh_from_db()
        assert user.check_password("S3cure-pass-123")

    def test_password_change_keeps_session(self, client, user):
        client.force_login(user)
        client.post(
            reverse("profile"),
            {
                "email": "reader@example.com",
                "current_password": "S3cure-pass-123",
                "new_password": "An0ther-strong-pass",
                "new_password_confirm": "An0ther-strong-pass",
            },
        )
        user.refresh_from_db()
        assert user.check_password("An0ther-strong-pass")
        assert client.get(reverse("profile")).status_code == 200

    def test_email_must_be_unique(self, client, user, staff):
        client.force_login(user)
        client.post(reverse("profile"), {"email": "staff@example.com"})
        user.refresh_from_db()
        assert user.email == "reader@example.com"

    def test_delete_account_requires_password(self, client, user):
        client.force_login(user)
        client.post(reverse("delete_account"), {"password": "wrong"})
        assert type(user).objects.filter(pk=user.pk).exists()
        client.post(reverse("delete_account"), {"password": "S3cure-pass-123"})
        assert not type(user).objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_category_with_books_cannot_be_deleted(book):
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        Category.objects.get(pk=book.category_id).delete()


@pytest.mark.django_db
def test_settings_post_does_not_claim_success(client, staff):
    client.force_login(staff)
    resp = client.post(reverse("dashboard_settings"), {"action": "backup"}, follow=True)
    text = resp.content.decode()
    assert "تم إنشاء النسخة الاحتياطية بنجاح!" not in text
    assert "غير مفعّلة" in text
