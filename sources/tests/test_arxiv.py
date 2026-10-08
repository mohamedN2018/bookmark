import xml.etree.ElementTree as ET
from pathlib import Path

from sources.providers.arxiv import ARX, OAI, ArxivProvider, categories_to_subjects

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_page.xml"


def _records():
    root = ET.parse(FIXTURE).getroot()
    return [ArxivProvider().normalize(r.find(f"{OAI}metadata/{ARX}arXiv")) for r in root.iter(OAI + "record")]


def test_cc_paper_is_hostable():
    cc = _records()[0]
    assert cc.source_record_id == "2306.07197"
    assert cc.title.startswith("AROID: Improving Adversarial Robustness")
    assert cc.year == 2024
    assert cc.content_type in {"PREPRINT", "RESEARCH_PAPER"}
    assert cc.subject_slugs == ["computer-vision", "artificial-intelligence", "machine-learning"]
    assert cc.license == "CC BY 4.0"
    assert cc.rights_status == "VERIFIED_FREE"
    assert [f.url for f in cc.files] == ["https://export.arxiv.org/pdf/2306.07197"]
    assert cc.authors


def test_arxiv_license_paper_is_link_only():
    restricted = _records()[1]
    assert restricted.source_record_id == "1806.11314"
    assert restricted.rights_status == "VERIFIED_RESTRICTED"
    assert restricted.access_status == "OPEN_ACCESS"
    assert restricted.access_verified
    assert restricted.files == []
    assert restricted.download_url == "https://arxiv.org/pdf/1806.11314"


def test_category_mapping():
    assert categories_to_subjects(["cs.LG", "stat.ML", "math.OC"]) == ["machine-learning", "mathematics"]
    assert categories_to_subjects(["hep-th", "astro-ph.CO"]) == ["theoretical-physics", "astronomy"]
