import pytest

from core.arabic import contains_arabic, normalize_arabic, normalize_key


@pytest.mark.parametrize(
    "variant",
    [
        "الذكاء الاصطناعي",
        "ذكاء اصطناعي",
        "الذكاء الإصطناعي",
        "الذَّكاءُ الاصطِناعيّ",
        "الذكـــاء الاصطناعي",
        "  الذكاء   الاصطناعي ",
    ],
)
def test_ai_variants_share_one_key(variant):
    assert normalize_key(variant) == "ذكاء اصطناعي"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("أحمد", "احمد"),
        ("إسلام", "اسلام"),
        ("آلة", "اله"),
        ("مستشفى", "مستشفي"),
        ("مدرسة", "مدرسه"),
        ("مسؤول", "مسوول"),
        ("قراءة", "قراءه"),
        ("سنة ٢٠٢٤", "سنه 2024"),
    ],
)
def test_character_folding(raw, expected):
    assert normalize_arabic(raw) == expected


def test_article_removed_with_attached_prepositions():
    assert normalize_key("والبرمجة بالحاسوب للمبتدئين") == "برمجه حاسوب مبتديين"


def test_short_words_starting_with_al_are_kept():
    # "الا" و"ال" وحدها لا تُقص إلى لا شيء
    assert normalize_key("ال") == "ال"


def test_mixed_arabic_english_query():
    assert normalize_key("Python البرمجة") == "python برمجه"
    assert normalize_key("Cyber-Security: الأمن السيبراني") == "cyber security امن سيبراني"


def test_latin_accents_and_case():
    assert normalize_arabic("Café ÉCOLE") == "cafe ecole"


def test_empty_values():
    assert normalize_arabic(None) == ""
    assert normalize_key("") == ""


def test_contains_arabic():
    assert contains_arabic("Python البرمجة")
    assert not contains_arabic("Clean Code")
