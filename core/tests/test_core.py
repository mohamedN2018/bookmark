import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory

from core.validators import validate_image_file, validate_pdf_file
from core.views import serve_public_media

PNG_1PX = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"


def test_pdf_validator_accepts_pdf():
    validate_pdf_file(SimpleUploadedFile("a.pdf", b"%PDF-1.7\n...", content_type="application/pdf"))


def test_pdf_validator_rejects_disguised_file():
    with pytest.raises(ValidationError):
        validate_pdf_file(SimpleUploadedFile("a.pdf", b"<html><script>", content_type="application/pdf"))


def test_image_validator_rejects_svg():
    with pytest.raises(ValidationError):
        validate_image_file(SimpleUploadedFile("a.png", b"<svg onload=alert(1)>", content_type="image/png"))


def test_image_validator_accepts_png():
    validate_image_file(SimpleUploadedFile("a.png", PNG_1PX, content_type="image/png"))


def test_dev_media_server_blocks_book_files():
    request = RequestFactory().get("/media/books/pdfs/x.pdf")
    with pytest.raises(Http404):
        serve_public_media(request, "books/pdfs/x.pdf")


@pytest.mark.django_db
def test_health(client):
    resp = client.get("/healthz/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": True}


def test_book_pdfs_are_not_served_in_production(client):
    assert client.get("/media/books/pdfs/anything.pdf").status_code == 404
