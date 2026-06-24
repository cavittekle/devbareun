"""Stable, privacy-safe provenance snapshots for analysis inputs.

The parser works from temporary local files and signed Supabase URLs. A saved
analysis result must therefore retain a durable, non-secret record of the exact
uploaded file identities and integrity states that were used to derive it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from ..version import APP_VERSION

PROVENANCE_SCHEMA_VERSION = "v1"


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _first(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _file_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return only analysis-relevant, share-safe file metadata.

    Storage paths, signed URLs, user ids and raw provider metadata are excluded
    intentionally. Hashes identify content but do not grant storage access.
    """
    declared = _text(row.get("checksum"))
    verified = _text(row.get("verified_checksum"))
    content_hash = verified or declared
    return {
        "file_id": _text(_first(row, "id", "file_id")),
        "filename": _text(_first(row, "original_filename", "original_name")) or "uploaded_file",
        "extension": _text(_first(row, "file_ext", "extension")),
        "size_bytes": _first(row, "size_bytes", "file_size_bytes"),
        "content_sha256": content_hash,
        "content_hash_source": "verified" if verified else ("declared" if declared else "unavailable"),
        "checksum_status": _text(row.get("checksum_status")) or "not_provided",
        "checksum_verified_at": row.get("checksum_verified_at"),
        "security_scan_status": _text(row.get("security_scan_status")) or "pending",
        "security_scan_engine": _text(row.get("security_scan_engine")),
        "security_scan_completed_at": row.get("security_scan_completed_at"),
        "quarantine_status": _text(row.get("quarantine_status")) or "pending_scan",
        "parser_status": _text(row.get("parser_status")) or "pending",
    }


def _canonical_bytes(records: Iterable[Dict[str, Any]]) -> bytes:
    return json.dumps(list(records), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def build_analysis_input_manifest(file_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a deterministic source manifest and SHA-256 fingerprint.

    ``source_fingerprint`` is calculated from the sorted source records only,
    not from ``captured_at`` or the app version. The same verified inputs always
    produce the same fingerprint across retries and worker restarts.
    """
    records: List[Dict[str, Any]] = [_file_record(dict(row or {})) for row in file_rows]
    records.sort(key=lambda item: (str(item.get("file_id") or ""), str(item.get("filename") or "")))
    source_fingerprint = hashlib.sha256(_canonical_bytes(records)).hexdigest()
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "analysis_engine_version": APP_VERSION,
        "file_count": len(records),
        "files": records,
        "source_fingerprint": source_fingerprint,
    }
