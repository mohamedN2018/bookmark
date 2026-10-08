"""تطبيع والتحقق من المعرّفات: ISBN-10 و ISBN-13 و DOI و ORCID."""

import re

from django.core.exceptions import ValidationError

_ISBN_CHARS = re.compile(r"[^0-9Xx]")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")
_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def clean_isbn(value):
    """يحذف الشرطات والمسافات ويوحّد X."""
    return _ISBN_CHARS.sub("", value or "").upper()


def is_valid_isbn10(value):
    isbn = clean_isbn(value)
    if not re.fullmatch(r"\d{9}[\dX]", isbn):
        return False
    total = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(isbn))
    return total % 11 == 0


def is_valid_isbn13(value):
    isbn = clean_isbn(value)
    if not re.fullmatch(r"\d{13}", isbn):
        return False
    total = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(isbn))
    return total % 10 == 0


def isbn10_to_isbn13(value):
    isbn = clean_isbn(value)
    if not is_valid_isbn10(isbn):
        return None
    core = "978" + isbn[:9]
    check = (10 - sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(core)) % 10) % 10
    return core + str(check)


def normalize_doi(value):
    """يعيد DOI بصيغة 10.xxxx/yyyy بأحرف صغيرة، أو "" إن كان غير صالح."""
    doi = (value or "").strip()
    for prefix in _DOI_PREFIXES:
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix) :]
            break
    doi = doi.strip().lower()
    return doi if _DOI.match(doi) else ""


def validate_isbn10(value):
    if value and not is_valid_isbn10(value):
        raise ValidationError("ISBN-10 غير صالح (خانة التحقق لا تطابق).")


def validate_isbn13(value):
    if value and not is_valid_isbn13(value):
        raise ValidationError("ISBN-13 غير صالح (خانة التحقق لا تطابق).")


def validate_doi(value):
    if value and not normalize_doi(value):
        raise ValidationError("DOI غير صالح. الصيغة: 10.xxxx/....")


def validate_orcid(value):
    if not value:
        return
    if not _ORCID.match(value):
        raise ValidationError("ORCID غير صالح. الصيغة: 0000-0000-0000-0000.")
    digits = value.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    expected = "X" if check == 10 else str(check)
    if digits[-1] != expected:
        raise ValidationError("ORCID غير صالح (خانة التحقق لا تطابق).")
