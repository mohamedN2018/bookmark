"""Project Gutenberg: كتب في الملكية العامة (في الولايات المتحدة).

نقرأ ملف الفهرس الرسمي pg_catalog.csv (الطريقة التي يوصي بها Gutenberg للوصول الجماعي)
ونربط بالقراءة والتحميل من موقعه، ولا نجلب الملفات من موقعه الرئيسي آليًا
(سياسة Gutenberg تمنع الزحف الآلي على الموقع الرئيسي).
"""

import csv
import io
import re

from core.net import fetch

from .base import NormalizedRecord, SourceProvider
from .subjects import locc_subjects, to_iso1

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"


class GutenbergProvider(SourceProvider):
    key = "gutenberg"
    name = "Project Gutenberg"
    allowed_hosts = ("www.gutenberg.org", "gutenberg.org")
    can_host_files = False
    request_delay = 0

    def iter_records(self, **params):
        body = fetch(CATALOG_URL, self.allowed_hosts, max_bytes=80 * 1024 * 1024, timeout=180)
        reader = csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace")))
        for row in reader:
            if row.get("Type") != "Text":
                continue
            yield row

    @staticmethod
    def _person(raw):
        # "Darwin, Charles, 1809-1882 [Editor]" -> "Charles Darwin"
        name = re.sub(r"\[[^\]]*\]", "", raw)
        name = re.sub(r",\s*-?\d{1,4}\??(?:\s*BCE?)?-?(?:\d{1,4}\??)?(?:\s*BCE?)?\s*$", "", name.strip())
        name = re.sub(r"\([^)]*\)", "", name).strip(" ,")
        parts = [p.strip() for p in name.split(",")]
        if len(parts) == 2 and parts[1]:
            return f"{parts[1]} {parts[0]}"
        return name

    def normalize(self, row):
        book_id = row["Text#"].strip()
        title_lines = [line.strip() for line in row.get("Title", "").split("\n") if line.strip()]
        authors = [self._person(a) for a in row.get("Authors", "").split(";") if a.strip()]
        locc = [c.strip() for c in row.get("LoCC", "").split(";") if c.strip()]
        languages = [code.strip() for code in row.get("Language", "").split(";") if code.strip()]
        page = f"https://www.gutenberg.org/ebooks/{book_id}"
        return NormalizedRecord(
            source_record_id=book_id,
            title=title_lines[0] if title_lines else "",
            subtitle=" ".join(title_lines[1:])[:500],
            record_url=page,
            authors=[a for a in authors if a and a.lower() not in {"various", "anonymous"}],
            language=to_iso1(languages[0]) if languages else "",
            content_type="BOOK",
            subject_slugs=locc_subjects(locc),
            keywords=[s.strip() for s in row.get("Subjects", "").split(";") if s.strip()][:10],
            cover_url=f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.cover.medium.jpg",
            read_url=f"https://www.gutenberg.org/ebooks/{book_id}.html.images",
            download_url=f"https://www.gutenberg.org/ebooks/{book_id}.epub3.images",
            access_status="PUBLIC_DOMAIN",
            rights_status="VERIFIED_FREE",
            license="Public Domain (USA) — Project Gutenberg",
            license_url="https://www.gutenberg.org/policy/license.html",
            source_owner="Project Gutenberg",
            rights_evidence=(
                "Project Gutenberg يصنّف هذا العمل في الملكية العامة في الولايات المتحدة. قد تختلف الحالة في دول أخرى."
            ),
            external_ids={"gutenberg": book_id},
        )
