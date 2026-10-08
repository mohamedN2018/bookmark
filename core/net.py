"""جلب آمن من الإنترنت (للاستيراد من المصادر الخارجية).

الحمايات:
- http/https فقط.
- قائمة نطاقات مسموحة لكل استدعاء (لا جلب لأي رابط عشوائي).
- حل DNS ورفض أي عنوان داخلي/خاص/loopback/link-local (منع SSRF)، ويُعاد الفحص بعد كل تحويل.
- حد أقصى للحجم يُطبَّق أثناء القراءة (لا يعتمد على Content-Length فقط).
- مهلة زمنية، User-Agent معرّف، وإعادة محاولة مع تأخير متزايد.
"""

import hashlib
import ipaddress
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

USER_AGENT = "MaktabaSirriya/1.0 (+https://bookmark.deplois.net; metadata harvester)"
DEFAULT_TIMEOUT = 60
MAX_REDIRECTS = 5


class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class UnsafeURL(FetchError):
    pass


def _host_allowed(host, allowed_hosts):
    host = (host or "").lower().rstrip(".")
    return any(host == h or host.endswith("." + h) for h in allowed_hosts)


def _assert_public(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError(f"تعذر حل النطاق: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise UnsafeURL(f"عنوان غير عام: {host} -> {ip}")


def validate_url(url, allowed_hosts):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURL(f"بروتوكول غير مسموح: {parsed.scheme}")
    if parsed.username or parsed.password:
        raise UnsafeURL("روابط ببيانات دخول غير مسموحة")
    if not parsed.hostname or not _host_allowed(parsed.hostname, allowed_hosts):
        raise UnsafeURL(f"نطاق غير مسموح: {parsed.hostname}")
    _assert_public(parsed.hostname)
    return parsed


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _open(url, allowed_hosts, timeout):
    for _ in range(MAX_REDIRECTS + 1):
        validate_url(url, allowed_hosts)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            return _opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                url = urljoin(url, exc.headers["Location"])
                continue
            raise FetchError(f"HTTP {exc.code}: {url}", status=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FetchError(f"{exc}: {url}") from exc
    raise FetchError(f"تحويلات كثيرة: {url}")


def fetch(url, allowed_hosts, *, max_bytes=50 * 1024 * 1024, timeout=DEFAULT_TIMEOUT, retries=2, backoff=3.0):
    """يعيد محتوى الرابط كـ bytes مع تطبيق كل الحمايات."""
    attempt = 0
    while True:
        try:
            with _open(url, allowed_hosts, timeout) as response:
                declared = response.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise FetchError(f"الملف أكبر من الحد ({int(declared)} > {max_bytes})")
                chunks, total = [], 0
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise FetchError(f"الملف أكبر من الحد ({max_bytes})")
                    chunks.append(chunk)
                return b"".join(chunks)
        except UnsafeURL:
            raise
        except FetchError as exc:
            # رفض صريح من الخادم: لا نعيد المحاولة
            if exc.status in (401, 403, 404, 410, 429):
                raise
            attempt += 1
            if attempt > retries:
                raise
            time.sleep(backoff * attempt)


def md5_hex(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()
