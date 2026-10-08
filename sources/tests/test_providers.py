import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sources.providers.gutenberg import GutenbergProvider
from sources.providers.licenses import classify_license
from sources.providers.oapen import OAI, OapenProvider, _flatten
from sources.providers.subjects import locc_subjects, thema_subjects, to_iso1

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("text", "uri", "expected"),
    [
        ("CC-BY-SA", "https://creativecommons.org/licenses/by-sa/4.0/", ("CREATIVE_COMMONS", "VERIFIED_FREE")),
        ("CC-BY-NC-ND", "", ("CREATIVE_COMMONS", "VERIFIED_FREE")),
        ("", "https://creativecommons.org/publicdomain/zero/1.0/", ("CREATIVE_COMMONS", "VERIFIED_FREE")),
        ("Public Domain", "", ("PUBLIC_DOMAIN", "VERIFIED_FREE")),
    ],
)
def test_known_licenses(text, uri, expected):
    assert classify_license(text, uri)[:2] == expected


@pytest.mark.parametrize("text", ["All rights reserved", "info:eu-repo/semantics/openAccess", "", "free"])
def test_unknown_licenses_are_not_free(text):
    assert classify_license(text) is None


def test_cc_label():
    assert classify_license("CC-BY-SA", "https://creativecommons.org/licenses/by-sa/4.0/")[2] == "CC BY-SA 4.0"


def test_subject_mapping_longest_prefix():
    assert thema_subjects(["UYQM", "UY", "PHN"]) == ["machine-learning", "computer-science", "nuclear-physics"]
    assert thema_subjects(["JNM"]) == []
    assert locc_subjects(["QC", "QA"]) == ["physics", "mathematics"]
    assert to_iso1("ara") == "ar"
    assert to_iso1("eng") == "en"
    assert to_iso1("xyz") == "other"


def _oapen_raw():
    root = ET.parse(FIXTURES / "oapen_record.xml").getroot()
    record = next(root.iter(OAI + "record"))
    fields, bitstreams = {}, []
    _flatten(record.find(OAI + "metadata")[0], [], fields, bitstreams)
    return {"identifier": "x", "fields": fields, "bitstreams": bitstreams}


def test_oapen_normalize_real_record():
    rec = OapenProvider().normalize(_oapen_raw())
    assert rec.source_record_id == "20.500.12657/101963"
    assert rec.title == "Wissenschaft weltoffen 2021"
    assert rec.language == "en"
    assert rec.year == 2022
    assert rec.doi == "10.3278/7004002tew"
    assert "9783763967605" in rec.isbns
    assert rec.page_count == 120
    assert rec.license == "CC BY-SA 4.0"
    assert rec.rights_status == "VERIFIED_FREE"
    assert len(rec.files) == 1
    assert rec.files[0].url.endswith("/9783763967605.pdf")
    assert rec.files[0].md5 == "b268de8d344faf7d1b98da18a2ee3da0"
    assert rec.cover_url.endswith(".jpg")
    # تصنيفه "تعليم عالٍ": لا يدخل المكتبة العلمية إلا مع --all-subjects
    assert rec.subject_slugs == []


def test_gutenberg_normalize_row():
    row = {
        "Text#": "2009",
        "Type": "Text",
        "Title": "On the Origin of Species By Means of Natural Selection\nOr, the Preservation",
        "Language": "en",
        "Authors": "Darwin, Charles, 1809-1882",
        "Subjects": "Evolution (Biology); Natural selection",
        "LoCC": "QH",
    }
    rec = GutenbergProvider().normalize(row)
    assert rec.title == "On the Origin of Species By Means of Natural Selection"
    assert rec.authors == ["Charles Darwin"]
    assert rec.subject_slugs == ["biology"]
    assert rec.access_status == "PUBLIC_DOMAIN"
    assert rec.read_url == "https://www.gutenberg.org/ebooks/2009.html.images"
    assert rec.files == []
