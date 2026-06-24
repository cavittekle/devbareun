"""Deterministic upload-security screening before parser execution.

This module is deliberately *not* an antivirus engine. It performs a bounded,
content-aware admission check over files that are already private in storage:

* validates the declared file signature again from the materialised bytes;
* rejects malformed or suspicious OOXML archives before openpyxl can read them;
* detects macro-enabled spreadsheets and active PDF constructs as findings;
* quarantines blocked files in metadata so they cannot be selected again.

A later external malware-scanner integration can add another scanner result, but
this gate must remain conservative and dependency-free for the worker runtime.
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

from .file_validation import validate_magic_signature
from .security_runtime import bool_env, int_env


SCREEN_ENGINE = "devbareun_heuristic_v1"
OFFICE_ARCHIVE_EXTENSIONS = {".xlsx", ".xlsm"}
PDF_ACTIVE_MARKERS = {
    b"/javascript": "pdf_javascript",
    b"/launch": "pdf_launch_action",
    b"/richmedia": "pdf_rich_media",
    b"/embeddedfile": "pdf_embedded_file",
}


class UploadSecurityScreeningError(ValueError):
    """A source file did not pass deterministic parser-admission screening."""

    def __init__(self, message: str, *, code: str, findings: List[Dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.findings = findings or []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _max_office_entries() -> int:
    return max(10, min(int_env("DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES", 2000), 10000))


def _max_office_uncompressed_bytes() -> int:
    default = max(64 * 1024 * 1024, int_env("DEVBAREUN_MAX_FILE_MB", 30) * 1024 * 1024 * 8)
    return max(8 * 1024 * 1024, int_env("DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES", default))


def _max_archive_ratio() -> int:
    return max(10, min(int_env("DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO", 500), 1000))


def _block_macro_enabled_uploads() -> bool:
    # Macro presence is recorded in all cases. Blocking remains a deployment
    # choice because some construction schedules legitimately arrive as XLSM.
    return bool_env("DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS", False)


def _block_active_pdf_content() -> bool:
    # Active PDF markers are not malware proof. They are a policy signal that
    # can be elevated to a block after a deployment decides to do so.
    return bool_env("DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT", False)


def _finding(code: str, *, severity: str = "warning") -> Dict[str, str]:
    return {"code": code, "severity": severity}


def _set_scan_state(file_row: Dict[str, Any], **patch: Any) -> None:
    file_row.update(patch)


def _quarantine(
    file_row: Dict[str, Any],
    *,
    code: str,
    findings: List[Dict[str, Any]],
    failed: bool = False,
) -> None:
    now = _now()
    _set_scan_state(
        file_row,
        security_scan_status="failed" if failed else "blocked",
        security_scan_engine=SCREEN_ENGINE,
        security_scan_completed_at=now,
        security_scan_error=code,
        security_scan_findings=findings,
        quarantine_status="quarantined",
        quarantine_reason=code,
        quarantined_at=now,
        upload_status="quarantined",
        status="quarantined",
        parser_status="blocked" if not failed else "failed",
    )


def _screen_office_archive(path: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > _max_office_entries():
                raise UploadSecurityScreeningError(
                    "Office workbook archive has too many entries for safe processing.",
                    code="office_archive_entry_limit",
                )
            total_uncompressed = 0
            macro_present = False
            max_ratio = _max_archive_ratio()
            for entry in entries:
                name = entry.filename.replace("\\", "/")
                pure = PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise UploadSecurityScreeningError(
                        "Office workbook archive contains an unsafe entry path.",
                        code="office_archive_path_traversal",
                    )
                if entry.is_dir():
                    continue
                total_uncompressed += max(0, int(entry.file_size or 0))
                if total_uncompressed > _max_office_uncompressed_bytes():
                    raise UploadSecurityScreeningError(
                        "Office workbook archive expands beyond the configured parser safety limit.",
                        code="office_archive_uncompressed_limit",
                    )
                compressed = max(0, int(entry.compress_size or 0))
                uncompressed = max(0, int(entry.file_size or 0))
                if uncompressed and (compressed == 0 or uncompressed / max(1, compressed) > max_ratio):
                    raise UploadSecurityScreeningError(
                        "Office workbook archive compression ratio exceeds the configured parser safety limit.",
                        code="office_archive_compression_ratio",
                    )
                if name.lower().endswith("vbaproject.bin"):
                    macro_present = True
            if macro_present:
                findings.append(_finding("macro_enabled_workbook"))
                if _block_macro_enabled_uploads():
                    raise UploadSecurityScreeningError(
                        "Macro-enabled workbooks are blocked by the current upload security policy.",
                        code="macro_enabled_workbook",
                        findings=findings,
                    )
    except UploadSecurityScreeningError:
        raise
    except zipfile.BadZipFile as exc:
        raise UploadSecurityScreeningError(
            "Office workbook archive is malformed or unreadable.",
            code="office_archive_invalid",
        ) from exc
    return findings


def _screen_pdf(path: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    # This is bounded evidence gathering, not full PDF interpretation.
    with path.open("rb") as handle:
        sample = handle.read(max(64 * 1024, int_env("DEVBAREUN_PDF_SECURITY_SAMPLE_BYTES", 1024 * 1024))).lower()
    for marker, code in PDF_ACTIVE_MARKERS.items():
        if marker in sample:
            findings.append(_finding(code))
    if findings and _block_active_pdf_content():
        raise UploadSecurityScreeningError(
            "PDF active content is blocked by the current upload security policy.",
            code="pdf_active_content",
            findings=findings,
        )
    return findings


def screen_materialized_upload(file_row: Dict[str, Any], path: Path) -> Dict[str, Any]:
    """Screen a downloaded/local file before parser execution.

    The mutable ``file_row`` is intentionally enriched in place. The analysis
    job service persists those fields with the checksum outcome after the parser
    stage succeeds or fails.
    """
    filename = str(file_row.get("original_filename") or file_row.get("original_name") or path.name)
    suffix = Path(filename).suffix.lower()
    now = _now()
    _set_scan_state(
        file_row,
        security_scan_status="scanning",
        security_scan_engine=SCREEN_ENGINE,
        security_scan_started_at=now,
        security_scan_error=None,
        security_scan_findings=[],
        quarantine_status="pending_scan",
        quarantine_reason=None,
        quarantined_at=None,
    )
    findings: List[Dict[str, Any]] = []
    try:
        if not path.exists() or not path.is_file():
            raise UploadSecurityScreeningError("Materialized upload is unavailable.", code="materialized_file_missing")
        with path.open("rb") as handle:
            signature = handle.read(4096)
        if not validate_magic_signature(signature, filename):
            raise UploadSecurityScreeningError(
                "File signature does not match the declared upload format.",
                code="signature_mismatch",
            )
        if suffix in OFFICE_ARCHIVE_EXTENSIONS:
            findings.extend(_screen_office_archive(path))
        elif suffix == ".pdf":
            findings.extend(_screen_pdf(path))
        completed_at = _now()
        _set_scan_state(
            file_row,
            security_scan_status="clean",
            security_scan_engine=SCREEN_ENGINE,
            security_scan_completed_at=completed_at,
            security_scan_error=None,
            security_scan_findings=findings,
            quarantine_status="released",
            quarantine_reason=None,
            quarantined_at=None,
        )
        return {"status": "clean", "engine": SCREEN_ENGINE, "findings": findings}
    except UploadSecurityScreeningError as exc:
        _quarantine(file_row, code=exc.code, findings=exc.findings or findings)
        raise
    except Exception as exc:
        _quarantine(file_row, code="screening_failure", findings=findings, failed=True)
        raise UploadSecurityScreeningError(
            "Upload security screening could not complete.",
            code="screening_failure",
            findings=findings,
        ) from exc
