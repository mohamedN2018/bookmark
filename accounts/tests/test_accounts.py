import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
class TestLogin:
    def test_open_redirect_is_blocked(self, client, user):
        resp = client.post(
            reverse("login") + "?next=https://evil.example.com/",
            {"username": "reader", "password": "S3cure-pass-123", "next": "https://evil.example.com/"},
        )
        assert resp.status_code == 302
        assert resp["Location"] == reverse("my_library")

    def test_internal_next_is_allowed(self, client, user):
        resp = client.post(reverse("login"), {"username": "reader", "password": "S3cure-pass-123", "next": "/books/"})
        assert resp["Location"] == "/books/"

    def test_wrong_password(self, client, user):
        resp = client.post(reverse("login"), {"username": "reader", "password": "nope"})
        assert resp.status_code == 400
        assert "_auth_user_id" not in client.session

    def test_rate_limited_per_username(self, client, user, settings):
        from django.core.cache import cache

        cache.clear()
        settings.LOGIN_MAX_FAILURES = 3
        for _ in range(3):
            client.post(reverse("login"), {"username": "reader", "password": "wrong"})
        resp = client.post(reverse("login"), {"username": "reader", "password": "S3cure-pass-123"})
        assert resp.status_code == 429
        assert "_auth_user_id" not in client.session

    def test_logout_requires_post(self, client, user):
        client.force_login(user)
        assert client.get(reverse("logout")).status_code == 405
        assert client.post(reverse("logout")).status_code == 302


@pytest.mark.django_db
def test_register_creates_and_logs_in(client):
    resp = client.post(
        reverse("register"),
        {
            "username": "newbie",
            "email": "n@example.com",
            "password1": "Strong-pass-987",
            "password2": "Strong-pass-987",
        },
    )
    assert resp.status_code == 302
    assert User.objects.filter(username="newbie").exists()


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
        assert User.objects.filter(pk=user.pk).exists()
        client.post(reverse("delete_account"), {"password": "S3cure-pass-123"})
        assert not User.objects.filter(pk=user.pk).exists()

    def test_superuser_cannot_self_delete(self, client, superuser):
        client.force_login(superuser)
        client.post(reverse("delete_account"), {"password": "S3cure-pass-123"})
        assert User.objects.filter(pk=superuser.pk).exists()
