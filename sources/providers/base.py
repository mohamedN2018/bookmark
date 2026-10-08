"""واجهة مزوّد المصدر (SourceProvider) والسجل المطبّع الذي تنتجه كل المزوّدات.

كل مزوّد جديد ينفّذ:
- iter_records(**params): يكتشف ويجلب السجلات الخام (Discover + Fetch).
- normalize(raw): يحوّل السجل الخام إلى NormalizedRecord (Parse + Normalize + Classify).
- validate(record): قائمة أخطاء؛ السجل الذي فيه أخطاء لا يُستورد.
الإزالة المكررة والإدخال في الفهرس والتنزيل مسؤولية sources.pipeline (مشتركة لكل المزوّدات).
"""

from dataclasses import dataclass, field


@dataclass
class FileRef:
    url: str
    mime: str = "application/pdf"
    size: int | None = None
    md5: str = ""


@dataclass
class NormalizedRecord:
    source_record_id: str
    title: str
    record_url: str = ""
    subtitle: str = ""
    authors: list = field(default_factory=list)
    editors: list = field(default_factory=list)
    description: str = ""
    language: str = ""  # ISO 639-1 مثل ar, en
    year: int | None = None
    publisher: str = ""
    isbns: list = field(default_factory=list)
    doi: str = ""
    page_count: int | None = None
    content_type: str = "BOOK"
    subject_slugs: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    cover_url: str = ""
    files: list = field(default_factory=list)  # [FileRef]
    read_url: str = ""
    download_url: str = ""
    access_status: str = "UNKNOWN"
    rights_status: str = "UNKNOWN"
    license: str = ""
    license_url: str = ""
    source_owner: str = ""
    rights_evidence: str = ""
    # حالة الوصول نفسها (مثل: القراءة مجانية على موقع المصدر) مأخوذة من بيانات المصدر الرسمية
    access_verified: bool = False
    external_ids: dict = field(default_factory=dict)


class SourceProvider:
    key = ""
    name = ""
    # النطاقات المسموح الجلب منها (SSRF)
    allowed_hosts = ()
    # هل يُسمح بتنزيل الملفات واستضافتها (يُشترط أيضًا ترخيص يسمح، لكل سجل)
    can_host_files = False
    # تأخير مهذّب بين الطلبات (ثوانٍ)
    request_delay = 1.0
    # تأخير بين تنزيلات الملفات (ثوانٍ)
    download_delay = 0.0

    def iter_records(self, **params):
        raise NotImplementedError

    def normalize(self, raw):
        raise NotImplementedError

    def validate(self, record):
        errors = []
        if not record.source_record_id:
            errors.append("لا يوجد معرّف للسجل في المصدر")
        if not record.title.strip():
            errors.append("لا يوجد عنوان")
        if record.year and not (1 <= record.year <= 2100):
            errors.append(f"سنة غير منطقية: {record.year}")
        return errors
