import pytest

from catalog.models import AccessLink, Edition, Person, Work
from core.net import md5_hex
from sources import pipeline as pipeline_module
from sources.models import ImportJob
from sources.pipeline import ImportPipeline
from sources.providers.base import FileRef, NormalizedRecord, SourceProvider

PDF = b"%PDF-1.7 fake book"


class FakeProvider(SourceProvider):
    key = "oapen"
    allowed_hosts = ("library.oapen.org",)
    can_host_files = True

    def __init__(self, records):
        self.records = records

    def iter_records(self, on_page=None, **params):
        yield from self.records

    def normalize(self, raw):
        return raw


def make_record(rid="1", **kw):
    data = {
        "source_record_id": rid,
        "title": "Deep Learning Basics",
        "authors": ["Ada Lovelace"],
        "language": "en",
        "year": 2021,
        "isbns": ["9780132350884"],
        "subject_slugs": ["deep-learning"],
        "record_url": f"https://library.oapen.org/handle/{rid}",
        "files": [
            FileRef(url=f"https://library.oapen.org/bitstream/{rid}/1/book.pdf", size=len(PDF), md5=md5_hex(PDF))
        ],
        "access_status": "CREATIVE_COMMONS",
        "rights_status": "VERIFIED_FREE",
        "license": "CC BY 4.0",
    }
    data.update(kw)
    return NormalizedRecord(**data)


def quiet(*_):
    pass


@pytest.fixture
def fake_fetch(monkeypatch):
    calls = []

    def _fetch(url, allowed_hosts, **kwargs):
        calls.append(url)
        return PDF

    monkeypatch.setattr(pipeline_module, "fetch", _fetch)
    return calls


@pytest.mark.django_db
def test_import_creates_catalog_and_hosts_licensed_file(fake_fetch, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    job = ImportPipeline(FakeProvider([make_record()]), download_files=True, log=quiet).run()
    assert (job.created, job.files_downloaded, job.errors) == (1, 1, 0)
    work = Work.objects.get()
    assert work.subjects.get().slug == "deep-learning"
    assert Person.objects.get().name == "Ada Lovelace"
    download = AccessLink.objects.get(link_type="DOWNLOAD")
    assert download.can_serve_hosted_file
    assert download.hosted_file.read().startswith(b"%PDF")


@pytest.mark.django_db
def test_import_is_idempotent(fake_fetch, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    ImportPipeline(FakeProvider([make_record()]), download_files=True, log=quiet).run()
    job = ImportPipeline(FakeProvider([make_record()]), download_files=True, log=quiet).run()
    assert (job.created, job.updated) == (0, 1)
    assert Work.objects.count() == 1
    assert AccessLink.objects.filter(link_type="DOWNLOAD").count() == 1
    assert len(fake_fetch) == 1


@pytest.mark.django_db
def test_same_isbn_from_another_record_is_duplicate(fake_fetch):
    records = [make_record("1"), make_record("2", title="Deep Learning Basics (copy)")]
    job = ImportPipeline(FakeProvider(records), log=quiet).run()
    assert (job.created, job.duplicates) == (1, 1)
    assert Edition.objects.count() == 1


@pytest.mark.django_db
def test_unlicensed_file_is_not_downloaded(fake_fetch):
    record = make_record(access_status="OPEN_ACCESS", rights_status="UNKNOWN", license="")
    job = ImportPipeline(FakeProvider([record]), download_files=True, log=quiet).run()
    assert job.files_downloaded == 0
    assert fake_fetch == []
    assert not AccessLink.objects.get(link_type="DOWNLOAD").allows_free_access


@pytest.mark.django_db
def test_md5_mismatch_rejected(fake_fetch, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    record = make_record(files=[FileRef(url="https://library.oapen.org/bitstream/1/1/b.pdf", md5="0" * 32)])
    job = ImportPipeline(FakeProvider([record]), download_files=True, log=quiet).run()
    assert job.files_downloaded == 0
    assert not AccessLink.objects.get(link_type="DOWNLOAD").hosted_file


@pytest.mark.django_db
def test_non_science_non_arabic_is_skipped(fake_fetch):
    records = [make_record("1", subject_slugs=[]), make_record("2", subject_slugs=[], language="ar", isbns=[])]
    job = ImportPipeline(FakeProvider(records), log=quiet).run()
    assert (job.skipped, job.created) == (1, 1)
    assert Work.objects.get().original_language == "ar"


@pytest.mark.django_db
def test_job_is_recorded(fake_fetch):
    ImportPipeline(FakeProvider([make_record()]), log=quiet).run()
    job = ImportJob.objects.get()
    assert job.status == "DONE"
    assert job.finished_at is not None
