from __future__ import annotations

import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Sequence

from ..analyzer import apply_baseline_actual_guardrails
from ..analysis_types import normalize_analysis_type, parser_analysis_type
from ..file_validation import validate_magic_signature
from ..models import ParsedProjectData
from ..parser import ConstructionFileParser
from ..security_runtime import int_env
from ..supabase_client import signed_download_url, settings as supabase_settings
from .premium_analysis import file_group_status


def normalize_parsed_project(
    parsed: ParsedProjectData,
    file_rows: Sequence[Dict[str, Any]] | None = None,
    project: Dict[str, Any] | None = None,
    analysis_type: str = "all",
) -> Dict[str, Any]:
    """Convert parser output into the v1.4.0 normalized analytics schema."""
    files = list(file_rows or [])
    canonical_type = normalize_analysis_type(analysis_type)
    confidence = _confidence_score(parsed)
    planned = parsed.planned_execution
    actual = parsed.actual_execution
    progress_variance = None
    if planned is not None and actual is not None:
        progress_variance = round(float(actual) - float(planned), 2)

    material_sheets = [sheet for sheet in parsed.sheets if sheet.detected_type in {"procurement", "material"}]
    schedule_sheets = [sheet for sheet in parsed.sheets if sheet.detected_type == "schedule"]
    uploaded_files = [row for row in files if str(row.get("upload_status") or row.get("status") or "").lower() not in {"deleted", "rejected"}]
    pending_review = [
        row for row in uploaded_files
        if str(row.get("parser_status") or row.get("status") or "pending").lower() in {"pending", "awaiting_upload", "uploaded", "processing"}
    ]
    approved = [
        row for row in uploaded_files
        if str(row.get("parser_status") or row.get("status") or "").lower() in {"parsed", "approved", "completed"}
    ]

    f2_amount = parsed.evidence.get("f2_completed_amount")
    approved_payment = f2_amount if f2_amount not in (None, "") else parsed.actual_cost
    contract_value = parsed.total_cost or (project or {}).get("contract_value")
    remaining_cost = None
    if contract_value not in (None, "") and approved_payment not in (None, ""):
        try:
            remaining_cost = round(float(contract_value) - float(approved_payment), 2)
        except Exception:
            remaining_cost = None

    result = {
        "project_info": {
            "project_id": (project or {}).get("id") or (project or {}).get("project_id"),
            "project_name": parsed.project_name or (project or {}).get("project_name") or "DevBareun Project",
            "project_code": (project or {}).get("project_code"),
            "location": (project or {}).get("location"),
            "client": (project or {}).get("client") or (project or {}).get("client_name"),
            "client_name": (project or {}).get("client_name") or (project or {}).get("client"),
            "contractor": (project or {}).get("contractor") or (project or {}).get("contractor_name"),
            "contractor_name": (project or {}).get("contractor_name") or (project or {}).get("contractor"),
            "report_date": (project or {}).get("report_date"),
            "currency": parsed.currency or (project or {}).get("currency") or "USD",
            "language_hint": parsed.language_hint,
            "source_file_count": len(uploaded_files),
            "analysis_type": canonical_type,
            "requested_analysis_type": analysis_type or "all",
        },
        "cost_data": [
            _metric("total_cost", contract_value),
            _metric("contract_value", contract_value),
            _metric("total_budget", parsed.total_cost or (project or {}).get("contract_value")),
            _metric("planned_cost", parsed.planned_cost),
            _metric("actual_cost", parsed.actual_cost),
            _metric("approved_payment", approved_payment),
            _metric("remaining_cost", remaining_cost),
            _metric("cost_variance", _safe_difference(parsed.actual_cost, contract_value)),
            _metric("cost_variance_percent", parsed.cost_variance_percent),
        ],
        "schedule_data": [
            {
                "baseline_start": None,
                "baseline_finish": parsed.baseline_finish,
                "planned_progress_percent": planned,
                "actual_progress_percent": actual,
                "forecast_finish": parsed.estimated_finish,
                "estimated_finish": parsed.estimated_finish,
                "delay_days": parsed.delay_days,
                "activity_name": None,
                "activity_status": None,
                "source_sheets": [sheet.to_dict() for sheet in schedule_sheets[:8]],
            }
        ],
        "progress_data": [
            _metric("planned_progress_percent", planned),
            _metric("actual_progress_percent", actual),
            _metric("progress_variance_percent", progress_variance),
        ],
        "manpower_data": [
            _metric("current_workforce", parsed.workforce_current),
            _metric("required_workforce", parsed.workforce_required),
            _metric("current_workers", parsed.workforce_current),
            _metric("required_workers", parsed.workforce_required),
            _metric("trade", None),
            _metric("productivity_rate", None),
            _metric("daily_output", None),
            _metric("planned_output", None),
            _metric("actual_output", None),
        ],
        "material_data": [
            {
                "detected_material_sources": len(material_sheets),
                "material_name": None,
                "required_quantity": None,
                "available_quantity": None,
                "used_quantity": None,
                "unit": None,
                "daily_consumption": None,
                "delivery_date": None,
                "supplier": None,
                "stock_status": None,
                "source_sheets": [sheet.to_dict() for sheet in material_sheets[:8]],
            }
        ],
        "risk_register_data": [],
        "milestones": _milestones_from_parsed(parsed),
        "document_control": {
            "uploaded_files": len(uploaded_files),
            "pending_review": len(pending_review),
            "approved_documents": len(approved),
            "missing_documents": max(0, 4 - len(uploaded_files)) if uploaded_files else 4,
            "files": [_file_summary(row) for row in uploaded_files[:50]],
        },
        "risk_signals": _risk_signals(parsed),
        "evidence": {
            "parser_evidence": parsed.evidence,
            "sheet_profiles": [sheet.to_dict() for sheet in parsed.sheets],
        },
        "warnings": list(dict.fromkeys(parsed.warnings)),
        "confidence_score": confidence,
    }
    result["file_group_status"] = file_group_status(result)
    return result


def parse_project_files(
    file_rows: Sequence[Dict[str, Any]],
    *,
    analysis_type: str = "all",
    project: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Parse uploaded project files and return normalized data.

    Supabase Storage objects are downloaded through signed URLs when credentials
    exist. Local development rows may also point to an existing local_path.
    """
    files = [row for row in file_rows if str(row.get("upload_status") or row.get("status") or "").lower() not in {"deleted", "rejected"}]
    warnings: List[str] = []
    with _materialized_files(files) as paths:
        if not paths:
            parsed = ParsedProjectData(
                project_name=(project or {}).get("project_name") or "DevBareun Project",
                currency=(project or {}).get("currency") or "USD",
                warnings=["No readable project files were available for parser execution."],
            )
        else:
            parser_type = parser_analysis_type(analysis_type)
            parser = ConstructionFileParser(analysis_type=analysis_type)
            parsed = parser.parse_files(paths)
            apply_baseline_actual_guardrails(parsed, parser_type)
        parsed.warnings.extend(w for w in warnings if w not in parsed.warnings)
        return normalize_parsed_project(parsed, files, project, analysis_type=analysis_type)


@contextmanager
def _materialized_files(file_rows: Sequence[Dict[str, Any]]) -> Iterator[List[Path]]:
    temp_dir = tempfile.TemporaryDirectory(prefix="devbareun_parse_")
    paths: List[Path] = []
    try:
        base = Path(temp_dir.name)
        for row in file_rows:
            local_path = row.get("local_path")
            if local_path and Path(str(local_path)).exists():
                paths.append(Path(str(local_path)))
                continue
            storage_path = row.get("storage_path")
            if not storage_path:
                continue
            downloaded = _download_storage_object(row, base)
            if downloaded:
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
                handle.write(chunk)
    if written <= 0:
        target.unlink(missing_ok=True)
        raise ValueError(f"Downloaded file was empty: {filename}")
    if not validate_magic_signature(bytes(first_bytes), filename):
        target.unlink(missing_ok=True)
        raise ValueError(f"File signature did not match allowed parser formats: {filename}")
    return target


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


def _safe_difference(left: Any, right: Any) -> float | None:
    if left in (None, "") or right in (None, ""):
        return None
    try:
        return round(float(left) - float(right), 2)
    except Exception:
        return None


def _file_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id") or row.get("file_id"),
        "filename": row.get("original_filename") or row.get("original_name"),
        "file_ext": row.get("file_ext") or row.get("extension"),
        "size_bytes": row.get("size_bytes") or row.get("file_size_bytes"),
        "status": row.get("upload_status") or row.get("status"),
        "parser_status": row.get("parser_status"),
    }


def _confidence_score(parsed: ParsedProjectData) -> float:
    score = 0.0
    if parsed.project_name:
        score += 10
    if parsed.currency:
        score += 8
    for field in ("planned_execution", "actual_execution", "total_cost", "actual_cost", "baseline_finish", "estimated_finish"):
        if getattr(parsed, field, None) not in (None, ""):
            score += 9
    if parsed.sheets:
        avg = sum(sheet.confidence for sheet in parsed.sheets) / max(1, len(parsed.sheets))
        score += min(28, avg * 0.28)
    if parsed.warnings:
        score -= min(18, len(parsed.warnings) * 3)
    return round(max(0, min(100, score)), 1)


def _risk_signals(parsed: ParsedProjectData) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    if parsed.delay_days and parsed.delay_days > 0:
        signals.append({"category": "Schedule delay", "value": parsed.delay_days, "unit": "days"})
    if parsed.cost_variance_percent and parsed.cost_variance_percent > 0:
        signals.append({"category": "Cost overrun", "value": parsed.cost_variance_percent, "unit": "%"})
    if parsed.workforce_current is not None and parsed.workforce_required and parsed.workforce_current < parsed.workforce_required:
        signals.append({"category": "Low manpower", "value": parsed.workforce_required - parsed.workforce_current, "unit": "workers"})
    for warning in parsed.warnings[:8]:
        signals.append({"category": "Data quality risk", "value": warning})
    return signals


def _milestones_from_parsed(parsed: ParsedProjectData) -> List[Dict[str, Any]]:
    milestones: List[Dict[str, Any]] = []
    if parsed.baseline_finish:
        milestones.append({"name": "Baseline Finish", "due_date": parsed.baseline_finish, "status": "Planned"})
    if parsed.estimated_finish:
        status = "Delayed" if parsed.delay_days and parsed.delay_days > 0 else "Upcoming"
        milestones.append({"name": "Forecast Finish", "due_date": parsed.estimated_finish, "status": status})
    return milestones
