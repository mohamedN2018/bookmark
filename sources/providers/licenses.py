"""تفسير الرخص. لا نعتبر أي رخصة "مجانية" إلا إذا تعرّفنا عليها صراحة."""

import re

# كل رخص المشاع الإبداعي تسمح بإعادة نشر النسخة كما هي مع النسبة لصاحبها
_CC = re.compile(r"(?:^|[/\s-])(by(?:-nc)?(?:-sa|-nd)?)(?:[/\s-]|$)", re.I)


def classify_license(text="", uri=""):
    """يعيد (access_status, rights_status, label, url) أو None إن كانت غير معروفة."""
    blob = f"{text} {uri}".strip().lower()
    if not blob:
        return None
    if "publicdomain/zero" in blob or re.search(r"\bcc0\b", blob):
        return (
            "CREATIVE_COMMONS",
            "VERIFIED_FREE",
            "CC0 1.0",
            uri or "https://creativecommons.org/publicdomain/zero/1.0/",
        )
    if "publicdomain/mark" in blob or "public domain" in blob:
        return ("PUBLIC_DOMAIN", "VERIFIED_FREE", "Public Domain", uri)
    if "creativecommons.org/licenses" in blob or blob.startswith("cc") or " cc-" in f" {blob}":
        match = _CC.search(blob.replace("cc-", "/").replace("cc ", "/"))
        variant = match.group(1).upper() if match else "BY"
        version = re.search(r"(\d\.\d)", blob)
        label = f"CC {variant} {version.group(1) if version else ''}".strip()
        return ("CREATIVE_COMMONS", "VERIFIED_FREE", label, uri)
    return None
