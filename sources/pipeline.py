"""خط الاستيراد المشترك لكل المزوّدات.

Discover/Fetch (المزوّد) → Normalize (المزوّد) → Validate → Filter → Deduplicate → Upsert → Download → Index
- Idempotent: نفس السجل من نفس المصدر يُحدَّث ولا يتكرر (unique: source + source_record_id).
- كشف التكرار عبر المصادر: ISBN ثم DOI ثم (العنوان المطبّع + أول مؤلف).
- لا يُستضاف ملف إلا إذا: المزوّد يسمح، والرخصة VERIFIED_FREE، والحجم ضمن الحد، و MD5 مطابق، والملف PDF فعلًا.
"""

import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from catalog.identifiers import clean_isbn, is_valid_isbn10, is_valid_isbn13, normalize_doi
from catalog.models import (
    AccessLink,
    Contribution,
    Edition,
    Person,
    Publisher,
    Subject,
    VerificationStatus,
    Work,
)
from core.arabic import normalize_key
from core.net import FetchError, fetch, md5_hex

from .models import ImportJob, Source

FREE_RIGHTS = "VERIFIED_FREE"


class ImportPipeline:
    def __init__(
        self,
        provider,
        *,
        download_files=False,
        science_only=True,
        languages=None,
        limit=None,
        max_total_bytes=None,
        log=print,
    ):
        self.provider = provider
        self.download_files = download_files and provider.can_host_files
        self.science_only = science_only
        self.languages = set(languages or [])
        self.limit = limit
        self.max_total_bytes = max_total_bytes or settings.IMPORT_MAX_TOTAL_MB * 1024 * 1024
        self.max_file_bytes = settings.MAX_PDF_UPLOAD_MB * 1024 * 1024
        self.log = log
        self.source = Source.objects.get(slug=provider.key)
        self._subjects = {s.slug: s for s in Subject.objects.all()}

    # ------------------------------------------------------------------ run
    def run(self, **params):
        job = ImportJob.objects.create(
            source=self.source,
            params={
                **{k: v for k, v in params.items() if isinstance(v, (str, int, bool))},
                "download_files": self.download_files,
                "science_only": self.science_only,
                "languages": sorted(self.languages),
                "limit": self.limit,
            },
        )
        imported = 0

        def remember_cursor(token):
            job.cursor = token or ""
            job.save(update_fields=["cursor"])

        try:
            for raw in self.provider.iter_records(on_page=remember_cursor, **params):
                job.seen += 1
                try:
                    outcome = self._process(raw, job)
                except Exception as exc:  # سجل واحد سيئ لا يوقف العملية
                    job.errors += 1
                    job.add_log(f"خطأ: {type(exc).__name__}: {exc}"[:500])
                    outcome = "error"
                if outcome in {"created", "updated", "duplicate"}:
                    imported += outcome == "created"
                if job.seen % 50 == 0:
                    job.save()
                    self.log(
                        f"[{self.provider.key}] مقروء {job.seen} · جديد {job.created} · محدّث {job.updated} · "
                        f"مكرر {job.duplicates} · تخطي {job.skipped} · "
                        f"ملفات {job.files_downloaded} · أخطاء {job.errors}"
                    )
                if self.limit and imported >= self.limit:
                    job.add_log(f"توقف عند الحد: {self.limit}")
                    break
            job.status = ImportJob.Status.DONE
        except Exception as exc:
            job.status = ImportJob.Status.FAILED
            job.add_log(f"فشل: {type(exc).__name__}: {exc}"[:1000])
            raise
        finally:
            job.finished_at = timezone.now()
            job.save()
            self.source.last_synced_at = job.finished_at
            self.source.health_status = (
                Source.Health.OK if job.status == ImportJob.Status.DONE else Source.Health.DEGRADED
            )
            self.source.save(update_fields=["last_synced_at", "health_status"])
        return job

    # ------------------------------------------------------------------ one record
    def _process(self, raw, job):
        record = self.provider.normalize(raw)
        problems = self.provider.validate(record)
        if problems:
            job.skipped += 1
            return "skipped"
        if self.languages and record.language not in self.languages:
            job.skipped += 1
            return "skipped"
        # المكتبة علمية أولًا: نقبل ما له موضوع علمي معروف، وكل ما هو بالعربية
        if self.science_only and not record.subject_slugs and record.language != "ar":
            job.skipped += 1
            return "skipped"

        with transaction.atomic():
            edition = Edition.objects.filter(source=self.source, source_record_id=record.source_record_id).first()
            if edition is not None:
                self._sync_links(edition, record, job)
                job.updated += 1
                return "updated"

            duplicate = self._find_duplicate(record)
            if duplicate is not None and isinstance(duplicate, Edition):
                # نفس الطبعة موجودة من مصدر آخر: نضيف طرق الوصول الجديدة فقط
                self._sync_links(duplicate, record, job)
                job.duplicates += 1
                return "duplicate"

            work = duplicate if isinstance(duplicate, Work) else self._create_work(record)
            edition = self._create_edition(work, record)
            self._sync_links(edition, record, job)
            if duplicate is None:
                job.created += 1
                return "created"
            job.duplicates += 1
            return "duplicate"

    def _isbns(self, record):
        isbn13, isbn10 = "", ""
        for raw in record.isbns:
            value = clean_isbn(raw)
            if not isbn13 and is_valid_isbn13(value):
                isbn13 = value
            elif not isbn10 and is_valid_isbn10(value):
                isbn10 = value
        return isbn13, isbn10

    def _find_duplicate(self, record):
        isbn13, isbn10 = self._isbns(record)
        if isbn13:
            found = Edition.objects.filter(isbn13=isbn13).first()
            if found:
                return found
        if isbn10:
            found = Edition.objects.filter(isbn10=isbn10).first()
            if found:
                return found
        doi = normalize_doi(record.doi)
        if doi:
            found = Edition.objects.filter(doi=doi).first()
            if found:
                return found
            work = Work.objects.filter(doi=doi).first()
            if work:
                return work
        if record.authors:
            key = normalize_key(record.title)
            author_key = normalize_key(record.authors[0])
            work = (
                Work.objects.filter(normalized_title=key, contributions__person__normalized_name=author_key)
                .distinct()
                .first()
            )
            if work:
                return work
        return None

    # ------------------------------------------------------------------ create
    def _person(self, name):
        key = normalize_key(name)
        person = Person.objects.filter(normalized_name=key).first()
        return person or Person.objects.create(name=name[:255], info_source=self.source.name)

    def _create_work(self, record):
        work = Work.objects.create(
            title=record.title[:500],
            subtitle=record.subtitle[:500],
            description=record.description,
            content_type=record.content_type,
            original_language=record.language,
            keywords=record.keywords,
            doi=normalize_doi(record.doi),
            external_ids=record.external_ids,
            verification_status=VerificationStatus.UNVERIFIED,
        )
        subjects = [self._subjects[s] for s in record.subject_slugs if s in self._subjects]
        if subjects:
            work.subjects.add(*subjects)
        for position, name in enumerate(record.authors):
            Contribution.objects.get_or_create(
                work=work, person=self._person(name), role=Contribution.Role.AUTHOR, defaults={"position": position}
            )
        for position, name in enumerate(record.editors):
            Contribution.objects.get_or_create(
                work=work, person=self._person(name), role=Contribution.Role.EDITOR, defaults={"position": position}
            )
        return work

    def _create_edition(self, work, record):
        isbn13, isbn10 = self._isbns(record)
        publisher = None
        if record.publisher:
            key = normalize_key(record.publisher)
            publisher = Publisher.objects.filter(normalized_name=key).first() or Publisher.objects.create(
                name=record.publisher[:255]
            )
        return Edition.objects.create(
            work=work,
            language=record.language,
            publication_year=record.year,
            page_count=record.page_count,
            publisher=publisher,
            isbn13=isbn13,
            isbn10=isbn10,
            doi=normalize_doi(record.doi),
            cover_url=record.cover_url[:1000],
            source=self.source,
            source_record_id=record.source_record_id,
            source_url=record.record_url[:1000],
            external_ids=record.external_ids,
            format=Edition.Format.DIGITAL,
        )

    # ------------------------------------------------------------------ access links
    def _link(self, edition, record, link_type, url="", **extra):
        free = record.rights_status == FREE_RIGHTS
        defaults = {
            "source": self.source,
            "access_status": record.access_status,
            "rights_status": record.rights_status,
            "license": record.license[:100],
            "license_url": record.license_url,
            "source_owner": record.source_owner[:255],
            "rights_evidence": record.rights_evidence,
            # الحقوق مأخوذة من بيانات المصدر الرسمية للسجل نفسه
            "verification_status": VerificationStatus.VERIFIED if free else VerificationStatus.UNVERIFIED,
            "verified_at": timezone.now() if free else None,
            "last_checked_at": timezone.now(),
            **extra,
        }
        link, created = AccessLink.objects.get_or_create(
            edition=edition, link_type=link_type, url=url[:2000], defaults=defaults
        )
        if not created:
            for field in ("access_status", "rights_status", "license", "license_url", "rights_evidence"):
                setattr(link, field, defaults[field])
            link.last_checked_at = timezone.now()
            link.save()
        return link

    def _sync_links(self, edition, record, job):
        if record.record_url:
            self._link(edition, record, AccessLink.LinkType.OFFICIAL_PAGE, record.record_url)
        if record.read_url and record.read_url != record.record_url:
            self._link(edition, record, AccessLink.LinkType.READ_ONLINE, record.read_url)
        if record.download_url:
            self._link(edition, record, AccessLink.LinkType.DOWNLOAD, record.download_url)
        for file_ref in record.files:
            link = self._link(edition, record, AccessLink.LinkType.DOWNLOAD, file_ref.url)
            if self.download_files and not link.hosted_file:
                self._download(link, file_ref, record, job)

    def _download(self, link, file_ref, record, job):
        if record.rights_status != FREE_RIGHTS:
            return
        if file_ref.size and file_ref.size > self.max_file_bytes:
            job.add_log(f"تخطي ملف كبير ({file_ref.size // (1024 * 1024)}MB): {file_ref.url}")
            return
        if job.bytes_downloaded + (file_ref.size or 0) > self.max_total_bytes:
            return
        try:
            data = fetch(file_ref.url, self.provider.allowed_hosts, max_bytes=self.max_file_bytes, timeout=300)
        except FetchError as exc:
            job.add_log(f"فشل تنزيل {file_ref.url}: {exc}"[:400])
            job.errors += 1
            return
        if not data.startswith(b"%PDF-"):
            job.add_log(f"الملف ليس PDF: {file_ref.url}")
            return
        if file_ref.md5 and md5_hex(data) != file_ref.md5.lower():
            job.add_log(f"MD5 غير مطابق: {file_ref.url}")
            job.errors += 1
            return
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "-", record.source_record_id)[:80]
        link.hosted_file.save(f"{self.provider.key}-{safe_id}.pdf", ContentFile(data), save=True)
        job.files_downloaded += 1
        job.bytes_downloaded += len(data)
