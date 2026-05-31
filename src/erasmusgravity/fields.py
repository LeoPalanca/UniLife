"""ISCED-F field of study -> NACE economic sector mapping.

Erasmus mobility records carry an ISCED-F "Field of Education" (sometimes prefixed
with a 4-digit code such as "0410 - Business and administration", sometimes a
plain label such as "Engineering"). For the field-level gravity / COVID-DiD
analysis we collapse each record to its **broad** ISCED-F field (the 2-digit
parent, "00".."10") and map that to a dominant NACE Rev2 letter sector. This is
a judgmental mapping and is explicit by design so it can be challenged in the
write-up.

Broad ISCED-F fields:

    00  Generic programmes               -> (no sector mapping; dropped)
    01  Education                        -> P  Education
    02  Arts and humanities              -> R  Arts, entertainment, recreation
    03  Social sciences, journalism      -> M  Professional, scientific, technical
    04  Business, administration, law    -> K  Financial and insurance
    05  Natural sciences, maths, stats   -> M  Professional, scientific, technical
    06  ICT                              -> J  Information and communication
    07  Engineering, manufacturing       -> C  Manufacturing
    08  Agriculture, forestry, fisheries -> A  Agriculture
    09  Health and welfare               -> Q  Human health and social work
    10  Services                         -> I  Accommodation and food service
"""
from __future__ import annotations

import re

BROAD_LABEL = {
    "01": "Education", "02": "Arts and humanities",
    "03": "Social sciences, journalism and information",
    "04": "Business, administration and law",
    "05": "Natural sciences, mathematics and statistics",
    "06": "Information and Communication Technologies",
    "07": "Engineering, manufacturing and construction",
    "08": "Agriculture, forestry, fisheries and veterinary",
    "09": "Health and welfare", "10": "Services",
}

# Broad ISCED-F code -> NACE Rev2 letter sector (one-to-one; judgmental)
ISCED_TO_NACE = {
    "01": "P", "02": "R", "03": "M", "04": "K", "05": "M",
    "06": "J", "07": "C", "08": "A", "09": "Q", "10": "I",
}

# Keyword fallback for records that carry only a text label (no leading 4-digit code).
# Order matters: first match wins, so list more specific terms before generic ones.
LABEL_RULES: list[tuple[str, str]] = [
    (r"\b(teacher|education|pedagog)", "01"),
    (r"\b(art|humanit|music|theatre|design|fashion|literature|linguistic|language|history|archaeolog|philosoph|religion)", "02"),
    (r"\b(political|sociolog|journalism|psycholog|social|anthropolog|communication studies|media studies)", "03"),
    (r"\b(business|administration|management|economic|finance|account|marketing|law|legal)", "04"),
    (r"\b(physics|chemistry|biolog|mathemat|statistic|earth|geolog|environment|astronom)", "05"),
    (r"\b(comput|software|informatics|ict|information and communication technolog|database|ai)", "06"),
    (r"\b(engineer|mechan|electric|electronic|construction|architect|manufacture|metal trade|civil)", "07"),
    (r"\b(agricultur|forestr|fisher|veterinar|horticult)", "08"),
    (r"\b(medic|nurs|health|dent|pharma|welfare|therap|public health)", "09"),
    (r"\b(tourism|hospitality|transport service|security|hairdress|cosmetic|sport|leisure)", "10"),
]


def to_broad_code(field_label: str | None) -> str | None:
    """Return the 2-digit ISCED-F broad code for a Field-of-Education label.

    Handles both code-prefixed values ("0410 - Business...") and plain labels.
    Returns None for generic programmes (00 / Unknown / not classified).
    """
    if field_label is None or not isinstance(field_label, str):
        return None
    s = field_label.strip()
    if not s:
        return None
    m = re.match(r"^(\d{2})\d{2}\b", s)
    if m:
        code = m.group(1)
        return code if code != "00" else None
    s_lower = s.lower()
    if any(w in s_lower for w in ("unknown", "not classified", "generic", "elsewhere classified")):
        return None
    for pat, code in LABEL_RULES:
        if re.search(pat, s_lower):
            return code
    return None


def to_nace(broad_code: str | None) -> str | None:
    return ISCED_TO_NACE.get(broad_code) if broad_code else None
