import pytest

from core.net import UnsafeURL, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://library.oapen.org/x",
        "https://evil.example.com/x",
        "https://user:pass@library.oapen.org/x",
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
    ],
)
def test_unsafe_urls_rejected(url):
    with pytest.raises(UnsafeURL):
        validate_url(url, ("library.oapen.org",))


def test_private_ip_behind_allowed_name_rejected(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(None, None, None, None, ("10.0.0.5", 0))])
    with pytest.raises(UnsafeURL):
        validate_url("https://library.oapen.org/x", ("library.oapen.org",))


def test_public_ip_allowed(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(None, None, None, None, ("93.184.216.34", 0))])
    validate_url("https://sub.library.oapen.org/x", ("library.oapen.org",))
