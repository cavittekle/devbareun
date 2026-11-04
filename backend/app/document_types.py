"""Document types a project upload can have, and the formats each accepts.

A delay analysis is built from three kinds of project documents:

* ``contract``  - the construction contract (müqavilə): PDF, Word or a photo/scan
* ``schedule``  - the programme (planlama): Excel/CSV, Primavera XER, MS Project
  XML/MPP, or a PDF print
* ``f2``        - F2 certificates of completed work (görülmüş işlərin aktı) used
  for payment: Excel/CSV or Word
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, FrozenSet, Optional

CONTRACT = "contract"
SCHEDULE = "schedule"
F2 = "f2"
DOCUMENT_TYPES = (CONTRACT, SCHEDULE, F2)

FORMATS_BY_TYPE: Dict[str, FrozenSet[str]] = {
    CONTRACT: frozenset({".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".webp"}),
    SCHEDULE: frozenset({".xlsx", ".xls", ".xlsm", ".csv", ".xer", ".xml", ".mpp", ".pdf"}),
    F2: frozenset({".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".doc"}),
}

ALL_FORMATS: FrozenSet[str] = frozenset().union(*FORMATS_BY_TYPE.values())

# Formats the analysis reads for calculations. Everything else is kept with
# the analysis as a supporting document and listed in the report.
READABLE_FORMATS: Dict[str, FrozenSet[str]] = {
    CONTRACT: frozenset(),
    SCHEDULE: frozenset({".xlsx", ".xls", ".xlsm", ".csv", ".xer", ".xml"}),
    F2: frozenset({".xlsx", ".xls", ".xlsm", ".csv", ".docx"}),
}

_TRANSLIT = str.maketrans({"ə": "e", "ı": "i", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u", "İ": "i", "Ə": "e"})


def _norm(value: str) -> str:
    text = str(value or "").lower().translate(_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize_document_type(value: Optional[str]) -> Optional[str]:
    """Return a known document type or ``None``."""
    text = _norm(value or "").strip().replace("-", "_").replace(" ", "_")
    aliases = {
        "contract": CONTRACT, "muqavile": CONTRACT, "sozlesme": CONTRACT,
        "schedule": SCHEDULE, "planning": SCHEDULE, "plan": SCHEDULE, "planlama": SCHEDULE, "programme": SCHEDULE,
        "f2": F2, "f_2": F2, "payment": F2, "odenis": F2, "akt": F2,
    }
    return aliases.get(text)


def infer_document_type(filename: str) -> str:
    """Best guess for files uploaded without a type (older clients)."""
    name = _norm(Path(filename or "").stem)
    ext = Path(filename or "").suffix.lower()
    if re.search(r"(^|[^a-z0-9])f[\s_-]?2([^0-9]|$)|forma[\s_-]?2|(^|[^a-z])akt(lar|i|[^a-z]|$)|odenis|qebul", name):
        return F2
    if re.search(r"muqavil|contract|sozlesme|dogovor|договор", name):
        return CONTRACT
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"}:
        return CONTRACT
    return SCHEDULE


def validate_document_format(document_type: str, filename: str) -> None:
    """Raise ``ValueError`` when the file format does not fit the document type."""
    ext = Path(filename or "").suffix.lower()
    allowed = FORMATS_BY_TYPE.get(document_type)
    if allowed is None:
        raise ValueError(f"Unknown document type: {document_type}")
    if ext not in allowed:
        formats = ", ".join(sorted(item.lstrip(".") for item in allowed))
        raise ValueError(f"{ext or 'This file'} is not accepted for {document_type} documents. Accepted: {formats}.")
