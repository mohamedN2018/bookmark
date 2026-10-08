import pytest
from django.urls import reverse


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    ["work", "edition", "person", "subject", "accesslink", "publisher", "series", "worktranslation"],
)
def test_catalog_admin_pages_render(client, superuser, verified_pd_link, model):
    client.force_login(superuser)
    assert client.get(reverse(f"admin:catalog_{model}_changelist")).status_code == 200
    assert client.get(reverse(f"admin:catalog_{model}_add")).status_code == 200


@pytest.mark.django_db
def test_work_admin_shows_quality(client, superuser, work):
    client.force_login(superuser)
    resp = client.get(reverse("admin:catalog_work_change", args=[work.id]))
    assert resp.status_code == 200
    assert "/100" in resp.content.decode()


@pytest.mark.django_db
def test_legacy_admin_is_read_only(client, superuser):
    client.force_login(superuser)
    assert client.get(reverse("admin:books_book_add")).status_code == 403


@pytest.mark.django_db
def test_sources_admin(client, superuser):
    client.force_login(superuser)
    assert client.get(reverse("admin:sources_source_changelist")).status_code == 200
