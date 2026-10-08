"""OAPEN Library: كتب أكاديمية مفتوحة الوصول محكّمة، بترخيص Creative Commons صريح لكل ملف.

الجلب عبر OAI-PMH (metadataPrefix=xoai) لأن REST API يتطلب تسجيلًا مسبقًا.
الرخصة تُؤخذ من حقل rightsuri/rights للملف نفسه (bitstream). روابط ملفات PDF تُحفظ كروابط تحميل
مباشرة من OAPEN (خادم الملفات يرفض التنزيل الآلي، فلا نستضيفها).
"""

import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from core.net import fetch

from .base import FileRef, NormalizedRecord, SourceProvider
from .licenses import classify_license
from .subjects import thema_subjects, to_iso1

OAI = "{http://www.openarchives.org/OAI/2.0/}"
XOAI = "{http://www.lyncode.com/xoai}"
ENDPOINT = "https://library.oapen.org/oai/request"
BOOKS_SET = "col_20.500.12657_6"
_THEMA_CODE = re.compile(r"::([A-Z][A-Z0-9]{0,7})\s")
_QUALIFIERS = {"none", "en_US", "*", "en", "ar"}


def _flatten(element, path, out, bitstreams):
    """يحوّل شجرة xoai إلى {path: [values]} مع تجاهل لاحقة اللغة، ويجمع الملفات."""
    for child in element:
        if child.tag == XOAI + "element":
            name = child.get("name")
            if name == "bitstream":
                fields = {f.get("name"): (f.text or "").strip() for f in child if f.tag == XOAI + "field"}
                bundle = path[-2] if len(path) >= 2 else ""
                fields["_bundle"] = bundle
                bitstreams.append(fields)
                continue
            if name == "bundle":
                bundle_name = next(
                    ((f.text or "").strip() for f in child if f.tag == XOAI + "field" and f.get("name") == "name"),
                    "",
                )
                _flatten(child, [*path, f"bundle:{bundle_name}"], out, bitstreams)
                continue
            _flatten(child, [*path, name], out, bitstreams)
        elif child.tag == XOAI + "field" and child.get("name") == "value":
            key_parts = path[:-1] if path and path[-1] in _QUALIFIERS else path
            out.setdefault(".".join(key_parts), []).append((child.text or "").strip())


class OapenProvider(SourceProvider):
    key = "oapen"
    name = "OAPEN Library"
    allowed_hosts = ("library.oapen.org",)
    # خادم ملفات OAPEN يرد 403 على الطلبات الآلية (حماية من البوتات)، فلا نستضيف الملفات
    # ونربط بها مباشرة؛ المستخدم ينزّلها من OAPEN عبر المتصفح.
    can_host_files = False
    request_delay = 1.5

    def iter_records(self, resume_token="", oai_set=BOOKS_SET, on_page=None, **params):
        token = resume_token
        while True:
            query = {"verb": "ListRecords"}
            if token:
                query["resumptionToken"] = token
            else:
                query.update({"metadataPrefix": "xoai", "set": oai_set})
            body = fetch(f"{ENDPOINT}?{urlencode(query)}", self.allowed_hosts, max_bytes=30 * 1024 * 1024, timeout=120)
            root = ET.fromstring(body)
            for record in root.iter(OAI + "record"):
                header = record.find(OAI + "header")
                if header is not None and header.get("status") == "deleted":
                    continue
                metadata = record.find(OAI + "metadata")
                if metadata is None or not len(metadata):
                    continue
                fields, bitstreams = {}, []
                _flatten(metadata[0], [], fields, bitstreams)
                identifier = header.findtext(OAI + "identifier", "") if header is not None else ""
                yield {"identifier": identifier, "fields": fields, "bitstreams": bitstreams}
            token_el = root.find(f".//{OAI}resumptionToken")
            token = (token_el.text or "").strip() if token_el is not None else ""
            if on_page:
                on_page(token)
            if not token:
                return
            time.sleep(self.request_delay)

    @staticmethod
    def _first(fields, *keys):
        for key in keys:
            values = [v for v in fields.get(key, []) if v]
            if values:
                return values[0]
        return ""

    @staticmethod
    def _person(name):
        # "Surname, Given" -> "Given Surname"
        if name.count(",") == 1:
            last, first = (p.strip() for p in name.split(","))
            if first and last:
                return f"{first} {last}"
        return name.strip()

    def normalize(self, raw):
        f = raw["fields"]
        handle_url = self._first(f, "dc.identifier.uri")
        handle = handle_url.rsplit("handle/", 1)[-1] if "handle/" in handle_url else raw["identifier"]

        pdfs = [
            b
            for b in raw["bitstreams"]
            if b.get("_bundle", "").endswith("ORIGINAL") and b.get("format") == "application/pdf" and b.get("url")
        ]
        thumbs = [b for b in raw["bitstreams"] if b.get("_bundle", "").endswith("THUMBNAIL") and b.get("url")]
        files = [
            FileRef(
                url=b["url"], size=int(b["size"]) if b.get("size", "").isdigit() else None, md5=b.get("checksum", "")
            )
            for b in pdfs
        ]

        license_info = None
        for b in pdfs:
            license_info = classify_license(b.get("rights", ""), b.get("rightsuri", ""))
            if license_info:
                break

        year_raw = self._first(f, "dc.date.issued")
        year = int(year_raw[:4]) if year_raw[:4].isdigit() else None
        pages_raw = self._first(f, "oapen.pages")
        codes = []
        for value in f.get("dc.subject.classification", []):
            codes += _THEMA_CODE.findall(value + " ")

        record = NormalizedRecord(
            source_record_id=handle,
            title=self._first(f, "dc.title"),
            subtitle=self._first(f, "dc.title.alternative"),
            record_url=handle_url,
            authors=[self._person(a) for a in f.get("dc.contributor.author", []) if a],
            editors=[self._person(e) for e in f.get("dc.contributor.editor", []) if e],
            description=self._first(f, "dc.description.abstract"),
            language=to_iso1(self._first(f, "dc.language")),
            year=year,
            publisher=self._first(f, "linkedItemsMetadata.oapen.relation.isPublishedBy.publisher.name"),
            isbns=[i.replace("-", "") for i in f.get("oapen.relation.isbn", []) if i],
            doi=self._first(f, "oapen.identifier.doi"),
            page_count=int(pages_raw) if pages_raw.isdigit() else None,
            content_type="BOOK",
            subject_slugs=thema_subjects(codes),
            keywords=[k for k in f.get("dc.subject.other", []) if k][:12],
            cover_url=thumbs[0]["url"] if thumbs else "",
            files=files,
            read_url=handle_url,
            source_owner=self._first(f, "linkedItemsMetadata.oapen.relation.isPublishedBy.publisher.name"),
            external_ids={"oapen_handle": handle},
        )
        if license_info:
            record.access_status, record.rights_status, record.license, record.license_url = license_info
            record.rights_evidence = f"رخصة الملف في بيانات OAPEN الوصفية: {license_info[2]}" + (
                f" ({license_info[3]})" if license_info[3] else ""
            )
        else:
            # كل محتوى OAPEN وصول مفتوح، لكن دون رخصة صريحة لا نستضيف الملف
            record.access_status = "OPEN_ACCESS"
            record.rights_status = "UNKNOWN"
            record.rights_evidence = "OAPEN: وصول مفتوح دون رخصة صريحة للملف في البيانات الوصفية."
        return record
