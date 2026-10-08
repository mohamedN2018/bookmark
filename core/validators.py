"""تحقق من الملفات المرفوعة: النوع الحقيقي (magic bytes) والحجم، وليس الامتداد فقط."""

from django.conf import settings
from django.core.exceptions import ValidationError

PDF_MAGIC = b"%PDF-"
IMAGE_MAGICS = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",  # JPEG
    b"RIFF",  # WEBP (يُتحقق من WEBP بعده)
    b"GIF87a",
    b"GIF89a",
)


def _head(f, n=16):
    pos = f.tell() if hasattr(f, "tell") else 0
    f.seek(0)
    data = f.read(n)
    f.seek(pos)
    return data


def _is_new_upload(f):
    # FieldFile محفوظ مسبقًا => _committed=True؛ لا نعيد فحصه (قد يكون مفقودًا من القرص)
    return not getattr(f, "_committed", False)


def validate_pdf_file(f):
    if not _is_new_upload(f):
        return
    limit = settings.MAX_PDF_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"حجم الملف أكبر من الحد المسموح ({settings.MAX_PDF_UPLOAD_MB} ميجابايت).")
    if not _head(f).startswith(PDF_MAGIC):
        raise ValidationError("الملف ليس PDF صالحًا.")


def validate_image_file(f):
    if not _is_new_upload(f):
        return
    limit = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"حجم الصورة أكبر من الحد المسموح ({settings.MAX_IMAGE_UPLOAD_MB} ميجابايت).")
    head = _head(f)
    if not head.startswith(IMAGE_MAGICS):
        raise ValidationError("نوع الصورة غير مدعوم (PNG أو JPEG أو WEBP أو GIF).")
    if head.startswith(b"RIFF") and head[8:12] != b"WEBP":
        raise ValidationError("نوع الصورة غير مدعوم.")
