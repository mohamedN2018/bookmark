"""arXiv: أبحاث ونسخ أولية (preprints) في العلوم والحاسب والرياضيات والفيزياء.

- البيانات الوصفية عبر OAI-PMH (metadataPrefix=arXiv) وتتضمن رخصة كل بحث.
- البحث برخصة Creative Commons: يُنزّل ملف PDF ويُستضاف (بمعدل طلب كل 3 ثوانٍ كما تطلب شروط arXiv).
- البحث برخصة arXiv الافتراضية (nonexclusive-distrib): القراءة مجانية على arXiv لكن إعادة الاستضافة
  غير مسموحة، فنربط به فقط.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from urllib.parse import urlencode

from core.net import fetch

from .base import FileRef, NormalizedRecord, SourceProvider
from .licenses import classify_license

OAI = "{http://www.openarchives.org/OAI/2.0/}"
ARX = "{http://arxiv.org/OAI/arXiv/}"
ENDPOINT = "https://oaipmh.arxiv.org/oai"
ARXIV_LICENSE = "arxiv.org/licenses/nonexclusive-distrib"

# من التصنيف الأدق إلى الأعم (أطول بادئة أولًا)
CATEGORY_TO_SUBJECT = [
    ("cs.AI", "artificial-intelligence"),
    ("cs.LG", "machine-learning"),
    ("stat.ML", "machine-learning"),
    ("cs.CL", "nlp"),
    ("cs.CV", "computer-vision"),
    ("cs.RO", "robotics"),
    ("cs.CR", "cryptography"),
    ("cs.DB", "databases"),
    ("cs.DC", "distributed-systems"),
    ("cs.NI", "networks"),
    ("cs.OS", "operating-systems"),
    ("cs.SE", "software-engineering"),
    ("cs.PL", "programming"),
    ("cs.GR", "computer-graphics"),
    ("cs.", "computer-science"),
    ("stat.", "statistics"),
    ("math.", "mathematics"),
    ("astro-ph", "astronomy"),
    ("nucl-", "nuclear-physics"),
    ("physics.ao-ph", "climate"),
    ("physics.geo-ph", "earth-sciences"),
    ("physics.chem-ph", "chemistry"),
    ("hep-", "theoretical-physics"),
    ("gr-qc", "theoretical-physics"),
    ("quant-ph", "physics"),
    ("cond-mat", "physics"),
    ("physics.", "physics"),
    ("q-bio", "biology"),
    ("eess.", "electrical-engineering"),
    ("econ.", "economics"),
    ("q-fin", "economics"),
]


def categories_to_subjects(categories):
    found = []
    for category in categories:
        for prefix, slug in CATEGORY_TO_SUBJECT:
            if category.startswith(prefix):
                if slug not in found:
                    found.append(slug)
                break
    return found


def _text(element, tag):
    value = element.findtext(ARX + tag) or ""
    return re.sub(r"\s+", " ", value).strip()


class ArxivProvider(SourceProvider):
    key = "arxiv"
    name = "arXiv"
    allowed_hosts = ("oaipmh.arxiv.org", "export.arxiv.org")
    can_host_files = True
    request_delay = 3.0
    download_delay = 3.0

    def iter_records(self, resume_token="", oai_set="cs", days=30, on_page=None, **params):
        token = resume_token
        while True:
            query = {"verb": "ListRecords"}
            if token:
                query["resumptionToken"] = token
            else:
                query.update(
                    {
                        "metadataPrefix": "arXiv",
                        "set": oai_set,
                        "from": (date.today() - timedelta(days=int(days))).isoformat(),
                    }
                )
            body = fetch(f"{ENDPOINT}?{urlencode(query)}", self.allowed_hosts, max_bytes=60 * 1024 * 1024, timeout=180)
            root = ET.fromstring(body)
            for record in root.iter(OAI + "record"):
                header = record.find(OAI + "header")
                if header is not None and header.get("status") == "deleted":
                    continue
                meta = record.find(f"{OAI}metadata/{ARX}arXiv")
                if meta is not None:
                    yield meta
            token_el = root.find(f".//{OAI}resumptionToken")
            token = (token_el.text or "").strip() if token_el is not None else ""
            if on_page:
                on_page(token)
            if not token:
                return
            time.sleep(self.request_delay)

    def normalize(self, meta):
        arxiv_id = _text(meta, "id")
        authors = []
        for author in meta.iter(ARX + "author"):
            name = " ".join(
                filter(None, [_text(author, "forenames"), _text(author, "keyname"), _text(author, "suffix")])
            )
            if name:
                authors.append(name)
        categories = _text(meta, "categories").split()
        created = _text(meta, "created")
        license_uri = _text(meta, "license")
        journal_ref = _text(meta, "journal-ref")

        record = NormalizedRecord(
            source_record_id=arxiv_id,
            title=_text(meta, "title"),
            record_url=f"https://arxiv.org/abs/{arxiv_id}",
            authors=authors,
            description=_text(meta, "abstract"),
            language="en",
            year=int(created[:4]) if created[:4].isdigit() else None,
            doi=_text(meta, "doi"),
            content_type="RESEARCH_PAPER" if journal_ref else "PREPRINT",
            subject_slugs=categories_to_subjects(categories),
            keywords=categories,
            source_owner="المؤلفون (عبر arXiv)",
            external_ids={"arxiv": arxiv_id},
        )
        licence = classify_license("", license_uri)
        if licence:
            record.access_status, record.rights_status, record.license, record.license_url = licence
            record.files = [FileRef(url=f"https://export.arxiv.org/pdf/{arxiv_id}")]
            record.rights_evidence = f"رخصة البحث في بيانات arXiv الوصفية: {license_uri}"
        else:
            # القراءة مجانية على arXiv، لكن الرخصة لا تسمح بإعادة الاستضافة
            record.access_status = "OPEN_ACCESS"
            record.rights_status = "VERIFIED_RESTRICTED"
            record.license = "arXiv non-exclusive distribution" if ARXIV_LICENSE in license_uri else ""
            record.license_url = license_uri
            record.download_url = f"https://arxiv.org/pdf/{arxiv_id}"
            record.rights_evidence = "رخصة arXiv الافتراضية: القراءة والتحميل من arXiv فقط، دون إعادة استضافة."
        record.access_verified = True
        record.read_url = ""
        return record
