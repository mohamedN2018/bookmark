"""تطبيع النص العربي (والإنجليزي المختلط) لأغراض البحث ومطابقة السجلات المكررة.

القواعد:
- حذف التشكيل والتطويل.
- توحيد الهمزات: أ إ آ ٱ -> ا ، ؤ -> و ، ئ -> ي.
- ى -> ي ، ة -> ه.
- الأرقام العربية الهندية والفارسية -> 0-9.
- الحروف اللاتينية -> lowercase مع إزالة العلامات (é -> e).
- علامات الترقيم -> مسافة، ثم ضغط المسافات.
- (اختياري) حذف أداة التعريف "ال" وما يسبقها من حروف الجر/العطف الملتصقة.

مثال: "الذكاء الإصطناعي" و"ذكاء اصطناعي" و"الذَّكاء الاصطناعيّ" تنتج نفس المفتاح
عند strip_article=True: "ذكاء اصطناعي".
"""

import re
import unicodedata

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"

_CHAR_MAP = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ى": "ي",
        "ة": "ه",
        "ک": "ك",
        "ی": "ي",
        # أرقام عربية هندية
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
        # أرقام فارسية
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
    }
)

# كل ما ليس حرفًا أو رقمًا يصبح مسافة (يشمل ، ؛ ؟ وعلامات الترقيم اللاتينية)
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_SPACES = re.compile(r"\s+")

# بادئات تلتصق بأداة التعريف: وال، بال، كال، فال، لل
_ARTICLE = re.compile(r"^(?:[وفبكل]?ال|لل)(?=\w{2,})")

_ARABIC_LETTER = re.compile(r"[؀-ۿ]")


def _strip_latin_accents(text):
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not (unicodedata.combining(ch) and ord(ch) < 0x0600))


def normalize_arabic(text, strip_article=False):
    """يعيد نسخة مطبّعة من النص. لا يغيّر ترتيب الكلمات."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = _TASHKEEL.sub("", text).replace(_TATWEEL, "")
    text = text.translate(_CHAR_MAP)
    text = _strip_latin_accents(text).lower()
    text = _NON_WORD.sub(" ", text).replace("_", " ")
    tokens = _SPACES.sub(" ", text).strip().split(" ")
    if strip_article:
        tokens = [_ARTICLE.sub("", t) if _ARABIC_LETTER.match(t) else t for t in tokens]
    return " ".join(t for t in tokens if t)


def normalize_key(text):
    """مفتاح مطابقة صارم: تطبيع كامل مع حذف "ال". يُستخدم لكشف التكرار والبحث."""
    return normalize_arabic(text, strip_article=True)


def contains_arabic(text):
    return bool(text) and bool(_ARABIC_LETTER.search(text))
