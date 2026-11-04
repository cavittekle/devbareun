"""Work categories (iş növləri) and building detection.

Estimate sections and schedule activities are grouped into six construction
work types. The plan curve spreads each estimate section's value over the
schedule activities of the same work type in the same building.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

FRAME = "frame"
MASONRY = "masonry"
ENVELOPE = "envelope"
FINISHING = "finishing"
MEP = "mep"
SITE = "site"

CATEGORIES: Tuple[str, ...] = (FRAME, MASONRY, ENVELOPE, FINISHING, MEP, SITE)

LABELS: Dict[str, Dict[str, str]] = {
    FRAME: {"az": "Torpaq və dəmir-beton", "en": "Earthworks and reinforced concrete", "short_az": "Karkas", "short_en": "Frame"},
    MASONRY: {"az": "Hörgü", "en": "Masonry", "short_az": "Hörgü", "short_en": "Masonry"},
    ENVELOPE: {"az": "Dam, fasad, qapı-pəncərə", "en": "Roof, facade, doors and windows", "short_az": "Dam/fasad", "short_en": "Envelope"},
    FINISHING: {"az": "Tamamlama", "en": "Finishing works", "short_az": "Tamaml.", "short_en": "Finishing"},
    MEP: {"az": "MEP və lift", "en": "MEP and lifts", "short_az": "MEP", "short_en": "MEP"},
    SITE: {"az": "Ərazi abadlığı", "en": "Site works and landscaping", "short_az": "Ərazi", "short_en": "Site"},
}

# A work type cannot really progress before the one it depends on.
DEPENDS_ON: Dict[str, Optional[str]] = {
    FRAME: None,
    MASONRY: FRAME,
    ENVELOPE: MASONRY,
    FINISHING: ENVELOPE,
    MEP: ENVELOPE,
    SITE: None,
}

# Keywords are matched on transliterated lower-case text (ə→e, ş→s, ...).
# Strong words decide first (e.g. "döşəmə plitəsinin betonlanması" is frame
# because of "beton"); weak words only when no strong word matched.
_STRONG: Sequence[Tuple[str, Sequence[str]]] = (
    (SITE, ("abadliq", "abadlas", "xarici sebek", "nasosxana", "yasillas", "landscap", "site work", "external work",
            "external network", "pump station", "благоустр", "наружн")),
    (MEP, ("muhendis", "elektrik", "su techizat", "kanaliz", "istilik", "ventil", "kondisioner", "santexnik", "qaz techizat",
           "lift", "mebel", "yanginsond", "zeif cereyan", "mep", "hvac", "plumbing", "electric", "elevator", "furniture",
           "fire fight", "инженер", "электр", "водоснаб", "канализ", "отоплен", "вентиляц", "лифт", "мебел")),
    (FRAME, ("torpaq", "qazinti", "bunovre", "ozul", "karkas", "demir-beton", "demir beton", "beton", "armatur", "monolit",
             "qelib", "earthwork", "excavat", "foundation", "concrete", "rebar", "reinforc", "земл", "котлован",
             "фундамент", "каркас", "бетон", "арматур", "монолит")),
    (ENVELOPE, ("krovl", "fasad", "pencere", "vitraj", "kontur", "dam ortu", "roof", "facade", "window", "curtain wall",
                "envelope", "кровл", "фасад", "окн", "витраж")),
    (MASONRY, ("horgu", "kerpic", "ehengdasi", "ehenq dasi", "masonry", "brick", "blockwork", "кладк")),
    (FINISHING, ("suvaq", "bezek", "boya", "kafel", "malyar", "tamamlama", "seramik", "laminat", "m/k", "finishing",
                 "plaster", "paint", "tiling", "screed", "отделк", "штукатур", "покраск")),
)
_WEAK: Sequence[Tuple[str, Sequence[str]]] = (
    (SITE, ("erazi", "sebekeler", "seki", "yol ", "hasar", "территор")),
    (ENVELOPE, ("dam ", "dam-", "dam,", "dam/", "qapi", "door", "двер")),
    (MASONRY, ("divar", "arakesme", "partition", "wall", "перегород", "стен")),
    (FINISHING, ("doseme", "tavan", "floor", "ceiling", "finish", "пол ", "потол")),
    (FRAME, ("sutun", "plit", "frame", "structur")),
)


_TRANSLIT = str.maketrans({"ə": "e", "ı": "i", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u", "İ": "i", "Ə": "e", "Ş": "s",
                           "Ç": "c", "Ğ": "g", "Ö": "o", "Ü": "u"})


def _plain(text: str) -> str:
    value = str(text or "").translate(_TRANSLIT).lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def categorize(*texts: Optional[str]) -> Optional[str]:
    """Work type for a section/activity name, or ``None`` when unclear.

    Texts are tried in order (e.g. section first, then line name)."""
    for text in texts:
        if not text:
            continue
        plain = f" {_plain(text)} "
        for table in (_STRONG, _WEAK):
            for category, words in table:
                if any(word in plain for word in words):
                    return category
    return None


_BUILDING = re.compile(r"(?:bina|binasi|blok|korpus|building|block|bldg|корпус|здание|дом)\s*[-#:.]?\s*(?:no\.?|n)?\s*[-#:.]?\s*(\d{1,3}[a-zа-я]?)(?!\d)", re.IGNORECASE)
_BUILDING_SUFFIX = re.compile(r"(?<![\d.,])(\d{1,3})\s*[-№]?\s*(?:sayli|saylı)?\s*(?:bina|blok|korpus)", re.IGNORECASE)


def building_of(*texts: Optional[str]) -> Optional[str]:
    """``Bina-3`` style building key found in the texts, else ``None``."""
    for text in texts:
        if not text:
            continue
        plain = _plain(text)
        match = _BUILDING.search(plain) or _BUILDING_SUFFIX.search(plain)
        if match:
            return f"Bina-{match.group(1).upper()}"
    return None


def building_sort_key(name: Optional[str]) -> Tuple[int, str]:
    match = re.search(r"(\d+)", name or "")
    return (int(match.group(1)) if match else 10_000, name or "")


def label(category: str, lang: str, short: bool = False) -> str:
    entry = LABELS.get(category) or {}
    key = ("short_" if short else "") + ("az" if lang == "az" else "en")
    return entry.get(key) or category


def ordered(categories: List[str]) -> List[str]:
    return [c for c in CATEGORIES if c in categories]
