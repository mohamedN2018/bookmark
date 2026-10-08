"""مطابقة تصنيفات المصادر مع شجرة موضوعات المكتبة (catalog.Subject.slug).

- Thema (EDItEUR): يستخدمه OAPEN/DOAB، مثل "UYQM" = Machine learning.
- LoCC (مكتبة الكونغرس): يستخدمه Project Gutenberg، مثل "QC" = Physics.
المطابقة بأطول بادئة. ما لا يطابق شيئًا لا يُصنّف (لا نخمّن).
"""

THEMA_TO_SUBJECT = {
    "UYQM": "machine-learning",
    "UYQL": "nlp",
    "UYQV": "computer-vision",
    "UYQ": "artificial-intelligence",
    "UYA": "computer-science",
    "UY": "computer-science",
    "UM": "programming",
    "UN": "databases",
    "UL": "operating-systems",
    "UR": "cybersecurity",
    "UT": "networks",
    "UG": "computer-graphics",
    "UB": "computer-science",
    "U": "computer-science",
    "PBT": "statistics",
    "PB": "mathematics",
    "PG": "astronomy",
    "PHN": "nuclear-physics",
    "PH": "physics",
    "PNN": "organic-chemistry",
    "PN": "chemistry",
    "PSB": "biochemistry",
    "PSAK": "genetics",
    "PS": "biology",
    "RBP": "climate",
    "RB": "earth-sciences",
    "RN": "environment",
    "THV": "energy",
    "THK": "nuclear-energy",
    "TH": "energy",
    "TJ": "electronics",
    "TG": "mechanical-engineering",
    "TN": "civil-engineering",
    "TD": "chemical-engineering",
    "TRP": "aerospace-engineering",
    "TV": "agriculture",
    "TQ": "environment",
    "TB": "engineering",
    "T": "engineering",
    "MF": "biomedicine",
    "KC": "economics",
}

LOCC_TO_SUBJECT = {
    "QA": "mathematics",
    "QB": "astronomy",
    "QC": "physics",
    "QD": "chemistry",
    "QE": "earth-sciences",
    "QH": "biology",
    "QK": "biology",
    "QL": "biology",
    "QM": "biology",
    "QP": "biomedicine",
    "QR": "biology",
    "TK": "electrical-engineering",
    "TJ": "mechanical-engineering",
    "TA": "civil-engineering",
    "TP": "chemical-engineering",
    "TL": "aerospace-engineering",
    "T": "engineering",
    "S": "agriculture",
    "GE": "environment",
    "GB": "earth-sciences",
    "HB": "economics",
    "HC": "economics",
    "HD": "economics",
}


def _longest_prefix(code, table):
    code = (code or "").strip().upper()
    for length in range(len(code), 0, -1):
        if code[:length] in table:
            return table[code[:length]]
    return None


def thema_subjects(codes):
    found = []
    for code in codes:
        slug = _longest_prefix(code, THEMA_TO_SUBJECT)
        if slug and slug not in found:
            found.append(slug)
    return found


def locc_subjects(codes):
    found = []
    for code in codes:
        slug = _longest_prefix(code, LOCC_TO_SUBJECT)
        if slug and slug not in found:
            found.append(slug)
    return found


ISO639_2_TO_1 = {
    "ara": "ar",
    "eng": "en",
    "fre": "fr",
    "fra": "fr",
    "ger": "de",
    "deu": "de",
    "spa": "es",
    "tur": "tr",
    "per": "fa",
    "fas": "fa",
    "urd": "ur",
    "rus": "ru",
    "chi": "zh",
    "zho": "zh",
    "jpn": "ja",
}
KNOWN_ISO1 = {"ar", "en", "fr", "de", "es", "tr", "fa", "ur", "ru", "zh", "ja"}


def to_iso1(code):
    code = (code or "").strip().lower()
    if code in KNOWN_ISO1:
        return code
    return ISO639_2_TO_1.get(code, "other" if code else "")
