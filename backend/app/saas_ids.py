
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Literal

PREFIXES = {
    "project": "DB-PRJ",
    "file": "DB-FILE",
    "analysis": "DB-ANL",
    "report": "DB-RPT",
    "company": "DB-CMP",
    "guest_order": "DB-GST",
    "payment": "DB-PAY",
    "checkout": "DB-CHK",
    "subscription": "DB-SUB",
    "credit": "DB-CRD",
    "audit": "DB-AUD",
    "privacy": "DB-PRV",
    "activity": "DB-ACT",
}

EntityKind = Literal[
    "project", "file", "analysis", "report", "company", "guest_order",
    "payment", "checkout", "subscription", "credit", "audit", "privacy", "activity"
]


def make_public_id(kind: EntityKind, sequence: int | None = None) -> str:
    prefix = PREFIXES[kind]
    if sequence is None:
        stamp = datetime.now(timezone.utc).strftime("%y%m%d")
        suffix = token_urlsafe(4).replace("-", "").replace("_", "")[:6].upper()
        return f"{prefix}-{stamp}-{suffix}"
    return f"{prefix}-{sequence:06d}"


def make_guest_token() -> str:
    return token_urlsafe(32)


def expiry(days: int = 14) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
