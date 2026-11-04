from __future__ import annotations

import tempfile
import urllib.request
import hashlib
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Sequence

from ..analysis_types import DELAY_ANALYSIS_TYPE
from ..document_types import infer_document_type, normalize_document_type
from ..file_validation import normalize_sha256_checksum, validate_magic_signature
from ..upload_security import screen_materialized_upload
from ..security_runtime import int_env
from ..supabase_client import signed_download_url, settings as supabase_settings


def parse_project_files(
    file_rows: Sequence[Dict[str, Any]],
    *,
    analysis_type: str = DELAY_ANALYSIS_TYPE,
    project: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run the execution and delay analysis on a project's uploaded files.

    Supabase Storage objects are downloaded through signed URLs when credentials
    exist; local development rows may point to an existing ``local_path``. Every
    file is checksum-verified and security-screened before it is read. The
    returned dictionary is the saved ``normalized_data``; the full delay result
    is under ``delay_analysis``.
    """
    files = [row for row in file_rows if str(row.get("upload_status") or row.get("status") or "").lower() not in {"deleted", "rejected"}]
    with _materialized_files(files) as paths:
        types = {
            str(row.pop("_materialized_path")): _row_document_type(row)
            for row in files if row.get("_materialized_path")
        }
        delay = _delay_analysis(paths, project, types)
    return normalize_delay_result(delay, files, project)


def _row_document_type(row: Dict[str, Any]) -> str:
    """Stored type, or a guess from the file name for older uploads."""
    stored = normalize_document_type(row.get("document_type"))
    if stored:
        return stored
    return infer_document_type(str(row.get("original_filename") or row.get("original_name") or row.get("storage_path") or ""))


def _delay_analysis(paths: Sequence[Path], project: Dict[str, Any] | None, document_types: Dict[str, str] | None = None) -> Dict[str, Any]:
    if not paths:
        return {"ok": False, "error": {"en": "No readable project files.", "az": "Oxunan layihə faylı yoxdur."}}
    from ..delay import run_delay_analysis

    return run_delay_analysis(paths, project=project, document_types=document_types)


def normalize_delay_result(
    delay: Dict[str, Any],
    file_rows: Sequence[Dict[str, Any]] | None = None,
    project: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Summarise a delay analysis result in the stored ``normalized_data`` shape."""
    project = project or {}
    files = list(file_rows or [])
    kpis = delay.get("kpis") or {}
    info = delay.get("project") or {}
    planned = kpis.get("planned_progress_pct")
    actual = kpis.get("actual_progress_pct")
    warnings = [item.get("en") for item in delay.get("data_quality") or [] if item.get("en")]
    if not delay.get("ok"):
        warnings.insert(0, (delay.get("error") or {}).get("en") or "Delay analysis could not be completed.")
    return {
        "project_info": {
            "project_id": project.get("id") or project.get("project_id"),
            "project_name": project.get("project_name") or info.get("name") or "DevBareun Project",
            "project_code": project.get("project_code"),
            "location": project.get("location") or info.get("location"),
            "client_name": project.get("client_name") or project.get("client") or info.get("client"),
            "contractor_name": project.get("contractor_name") or project.get("contractor") or info.get("contractor"),
            "currency": info.get("currency") or project.get("currency"),
            "source_file_count": len(files),
            "analysis_type": DELAY_ANALYSIS_TYPE,
        },
        "schedule_data": [
            {
                "baseline_start": kpis.get("project_start"),
                "baseline_finish": kpis.get("planned_finish"),
                "data_date": kpis.get("data_date"),
                "planned_progress_percent": planned,
                "actual_progress_percent": actual,
                "forecast_finish": kpis.get("forecast_finish"),
                "delay_days": kpis.get("schedule_delay_days"),
                "forecast_delay_days": kpis.get("forecast_delay_days"),
                "spi": kpis.get("spi"),
                "status": kpis.get("status"),
            }
        ],
        "progress_data": [
            _metric("planned_progress_percent", planned),
            _metric("actual_progress_percent", actual),
            _metric("progress_variance_percent", kpis.get("progress_gap_pct")),
        ],
        "milestones": _milestones(kpis),
        "document_control": {
            "uploaded_files": len(files),
            "files": [_file_summary(row) for row in files[:50]],
        },
        "warnings": list(dict.fromkeys(warnings)),
        "confidence_score": _confidence_score(delay),
        "delay_analysis": delay,
    }


def _confidence_score(delay: Dict[str, Any]) -> float:
    """Share of the analysis that rests on supplied data, 0-100.

    Starts at 100 and loses points for each data-quality warning; a failed
    analysis scores 0.
    """
    if not delay.get("ok"):
        return 0.0
    penalty = {"critical": 25, "warning": 8, "info": 2}
    score = 100.0
    for item in delay.get("data_quality") or []:
        score -= penalty.get(item.get("severity"), 0)
    return round(max(0.0, min(100.0, score)), 1)


def _milestones(kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
    milestones: List[Dict[str, Any]] = []
    if kpis.get("planned_finish"):
        milestones.append({"name": "Contract finish", "due_date": kpis["planned_finish"], "status": "Planned"})
    if kpis.get("forecast_finish"):
        late = (kpis.get("forecast_delay_days") or 0) > 0
        milestones.append({"name": "Forecast finish", "due_date": kpis["forecast_finish"], "status": "Delayed" if late else "Upcoming"})
    return milestones


@contextmanager
def _materialized_files(file_rows: Sequence[Dict[str, Any]]) -> Iterator[List[Path]]:
    temp_dir = tempfile.TemporaryDirectory(prefix="devbareun_parse_")
    paths: List[Path] = []
    try:
        base = Path(temp_dir.name)
        for row in file_rows:
            local_path = row.get("local_path")
            if local_path and Path(str(local_path)).exists():
                local = Path(str(local_path))
                _verify_materialized_checksum(row, local)
                screen_materialized_upload(row, local)
                row["_materialized_path"] = str(local)
                paths.append(local)
                continue
            storage_path = row.get("storage_path")
            if not storage_path:
                continue
            downloaded = _download_storage_object(row, base)
            if downloaded:
                row["_materialized_path"] = str(downloaded)
                paths.append(downloaded)
        yield paths
    finally:
        temp_dir.cleanup()


def _download_storage_object(file_row: Dict[str, Any], base: Path) -> Path | None:
    storage_path = str(file_row.get("storage_path") or "")
    filename = str(file_row.get("original_filename") or file_row.get("original_name") or Path(storage_path).name or "uploaded_file")
    if not storage_path:
        return None
    signed = signed_download_url(storage_path, expires_in=600)
    url = _signed_url_to_absolute(signed)
    target = base / Path(filename).name
    max_bytes = int_env("DEVBAREUN_MAX_FILE_MB", 30) * 1024 * 1024
    first_bytes = bytearray()
    written = 0
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=30) as response:
        length_header = response.headers.get("Content-Length")
        if length_header:
            try:
                content_length = int(length_header)
            except Exception:
                content_length = None
            if content_length and content_length > max_bytes:
                target.unlink(missing_ok=True)
                raise ValueError(f"File is too large for parser download: {filename}.")
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    target.unlink(missing_ok=True)
                    raise ValueError(f"File is too large for parser download: {filename}.")
                if len(first_bytes) < 4096:
                    first_bytes.extend(chunk[: 4096 - len(first_bytes)])
                digest.update(chunk)
                handle.write(chunk)
    if written <= 0:
        target.unlink(missing_ok=True)
        raise ValueError(f"Downloaded file was empty: {filename}")
    if not validate_magic_signature(bytes(first_bytes), filename):
        target.unlink(missing_ok=True)
        raise ValueError(f"File signature did not match allowed parser formats: {filename}")
    _verify_materialized_checksum(file_row, target, actual_checksum=digest.hexdigest())
    screen_materialized_upload(file_row, target)
    return target


def _checksum_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verify_materialized_checksum(file_row: Dict[str, Any], path: Path, *, actual_checksum: str | None = None) -> None:
    """Verify source bytes against browser-provided SHA-256 before parsing.

    Mutable row fields are later persisted by the analysis job service; that keeps
    parser code storage-agnostic while still exposing integrity state in the UI.
    """
    filename = str(file_row.get("original_filename") or file_row.get("original_name") or path.name)
    try:
        expected = normalize_sha256_checksum(file_row.get("checksum"))
    except ValueError as exc:
        file_row.update({
            "checksum_status": "invalid",
            "checksum_error": "invalid_registered_checksum",
            "checksum_verified_at": _checksum_timestamp(),
        })
        raise ValueError(f"Invalid SHA-256 checksum metadata for {filename}.") from exc
    if actual_checksum is None:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_checksum = digest.hexdigest()
    file_row["verified_checksum"] = actual_checksum
    file_row["checksum_verified_at"] = _checksum_timestamp()
    if not expected:
        file_row["checksum_status"] = "not_provided"
        return
    if expected != actual_checksum:
        file_row.update({
            "checksum_status": "mismatch",
            "checksum_error": "checksum_mismatch",
        })
        raise ValueError(f"File checksum did not match the registered upload record: {filename}")
    file_row.update({
        "checksum_status": "verified",
        "checksum_error": None,
    })


def _signed_url_to_absolute(raw: Dict[str, Any]) -> str:
    url = raw.get("signedURL") or raw.get("signedUrl") or raw.get("signed_url") or raw.get("url")
    if not url:
        raise ValueError("Supabase Storage did not return a signed download URL.")
    text = str(url)
    if text.startswith("http"):
        return text
    cfg = supabase_settings()
    if text.startswith("/storage/v1"):
        return f"{cfg.url}{text}"
    if text.startswith("/"):
        return f"{cfg.url}/storage/v1{text}"
    return f"{cfg.url}/storage/v1/{text}"


def _metric(name: str, value: Any) -> Dict[str, Any]:
    return {"name": name, "value": value}


def _file_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id") or row.get("file_id"),
        "filename": row.get("original_filename") or row.get("original_name"),
        "file_ext": row.get("file_ext") or row.get("extension"),
        "document_type": _row_document_type(row),
        "size_bytes": row.get("size_bytes") or row.get("file_size_bytes"),
        "status": row.get("upload_status") or row.get("status"),
        "parser_status": row.get("parser_status"),
        "checksum_status": row.get("checksum_status") or "not_provided",
        "checksum_verified_at": row.get("checksum_verified_at"),
        "security_scan_status": row.get("security_scan_status") or "pending",
        "security_scan_engine": row.get("security_scan_engine"),
        "security_scan_completed_at": row.get("security_scan_completed_at"),
        "security_scan_findings": row.get("security_scan_findings") or [],
        "quarantine_status": row.get("quarantine_status") or "pending_scan",
    }
