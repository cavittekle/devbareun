from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from ..auth_dependencies import CurrentUser, local_store_enabled
from ..access_control import can_access_project_scope, is_staff_role
from .project_sharing_service import can_access_project_resource
from .project_activity_service import record_project_activity
from ..production_store import ProductionStoreError, call_rpc, first_existing, insert_row, is_configured, select_rows, uuid_like
from ..reports import build_excel_bytes, build_pdf_bytes
from .analysis_job_service import get_latest_analysis_result


REPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "reports"
REPORT_SNAPSHOT_VERSION = "v1"
PDF_MEDIA_TYPE = "application/pdf"
EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def list_project_reports(project_id: str, project: Dict[str, Any], user: CurrentUser) -> Dict[str, Any]:
    db_project_id = _project_db_id(project, project_id)
    if is_configured() and db_project_id:
        rows = select_rows("reports", {"project_id": db_project_id}, limit=200)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("reports", project_id=project_id)
    else:
        rows = []
    # Route-level project authorization already verified the caller. Filtering
    # by report owner here would hide frozen reports from explicitly shared
    # project viewers.
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {"project_id": project_id, "reports": [_report_api(row, project) for row in rows]}


def generate_report(project_id: str, project: Dict[str, Any], user: CurrentUser, report_format: str = "pdf", report_type: str = "Project Control Report") -> Dict[str, Any]:
    """Create an immutable report snapshot from the latest completed analysis.

    Production report rows retain the dashboard payload used at generation time.
    A later analysis cannot silently change what an existing report downloads.
    """
    fmt = normalize_report_format(report_format)
    safe_report_type = normalize_report_type(report_type)
    result = get_latest_analysis_result(project_id, project, user)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "analysis_missing", "message": "Run project performance review before generating a report."})

    payload = legacy_report_payload(project, result)
    content = build_excel_bytes(payload, lang="en") if fmt == "excel" else build_pdf_bytes(payload, lang="en", paper="a4")
    extension = "xlsx" if fmt == "excel" else "pdf"
    media_type = EXCEL_MEDIA_TYPE if fmt == "excel" else PDF_MEDIA_TYPE
    report_name = f"{project.get('project_name') or 'DevBareun Project'} {safe_report_type}"
    storage_path = _store_local_report(content, project_id, extension) if local_store_enabled() else None
    row = _insert_report_row(
        user=user,
        project=project,
        project_id=project_id,
        result=result,
        report_name=report_name,
        report_type=safe_report_type,
        fmt=fmt.upper(),
        storage_path=storage_path,
        media_type=media_type,
        report_payload=payload,
        payload_sha256=_payload_sha256(payload),
        content_sha256=_content_sha256(content),
    )
    try:
        record_project_activity(
            project,
            user,
            "report.generated",
            "report",
            str(row.get("report_id") or row.get("id") or "") or None,
            {"format": fmt, "report_type": safe_report_type, "snapshot_version": REPORT_SNAPSHOT_VERSION},
        )
    except Exception:
        pass
    return {"report": _report_api(row, project), "download_ready": True, "snapshot_version": REPORT_SNAPSHOT_VERSION}

def get_report_download(report_id: str, user: CurrentUser) -> Tuple[bytes, str, str]:
    """Return a user-authorized report file and record a successful download.

    Stored file content is preferred for local/pilot operation. In production,
    reports can be rendered again from the frozen ``report_payload`` snapshot.
    Legacy rows created before snapshot support retain a compatibility fallback.
    """
    report = _find_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Report was not found."})
    project = _find_project_for_report(report)
    # Legacy snapshots without a recoverable project row retain the original
    # direct-owner check. New/shared reports always authorize against the
    # project-scoped grant before file content is rendered.
    allowed = _report_project_access_allowed(project, user) if project else _row_belongs_to_user(report, user)
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You do not have permission to download this report."})

    fmt = normalize_report_format(report.get("format") or report.get("report_format") or "pdf")
    media_type = report.get("media_type") or (EXCEL_MEDIA_TYPE if fmt == "excel" else PDF_MEDIA_TYPE)
    filename = _safe_filename(report.get("report_name") or report.get("name") or "DevBareun_Report", "xlsx" if fmt == "excel" else "pdf")
    storage_path = report.get("storage_path")
    if storage_path and Path(str(storage_path)).exists():
        content = Path(str(storage_path)).read_bytes()
    else:
        payload = report.get("report_payload")
        if not isinstance(payload, dict) or not payload:
            project = _find_project_for_report(report)
            result = _find_result_for_report(report)
            if not result:
                raise HTTPException(status_code=404, detail={"error": "analysis_missing", "message": "Saved analysis result was not found for this report."})
            payload = legacy_report_payload(project or {}, result)
        content = build_excel_bytes(payload, lang="en") if fmt == "excel" else build_pdf_bytes(payload, lang="en", paper="a4")

    _record_report_download(report, user)
    if project:
        try:
            record_project_activity(
                project,
                user,
                "report.downloaded",
                "report",
                str(report.get("report_id") or report.get("id") or report_id) or None,
                {"format": fmt, "snapshot_available": bool(report.get("report_payload"))},
            )
        except Exception:
            pass
    return content, media_type, filename

def legacy_report_payload(project: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    dashboard_data = analysis_result.get("dashboard_data") or {}
    premium = dashboard_data.get("premium_dashboard") or {}
    metrics = dashboard_data.get("metrics") or {}
    risks = analysis_result.get("risk_data") or []
    if isinstance(risks, dict):
        risks = risks.get("risks") or risks.get("top_risks") or []
    project_name = project.get("project_name") or (dashboard_data.get("project") or {}).get("name") or "DevBareun Project"
    currency = (dashboard_data.get("project") or {}).get("currency") or project.get("currency") or "USD"
    summary = _summary_text(dashboard_data, risks)
    if premium:
        summary = _premium_summary_text(premium)
    premium_kpis = premium.get("kpis") or {}
    return {
        "project_id": str(project.get("id") or project.get("project_id") or analysis_result.get("project_id") or ""),
        "dashboard": {
            "project": {
                "name": project_name,
                "report_id": str(analysis_result.get("id") or analysis_result.get("analysis_id") or "DBR-REPORT"),
                "result_id": str(analysis_result.get("id") or analysis_result.get("analysis_id") or "DBR-RESULT"),
                "report_date": str(analysis_result.get("created_at") or datetime.utcnow().date().isoformat())[:10],
                "status": "Completed",
                "currency": currency,
                "confidence": analysis_result.get("confidence_score") or dashboard_data.get("confidence_score") or 0,
                "analysis_type": premium.get("analysis_type") or analysis_result.get("analysis_type") or "project_control",
                "dashboard_title": premium.get("title") or "Project Control Report",
                "dashboard_description": "Project-control dashboard combining schedule, cost, payment, workforce, material, risk and recovery actions." if premium else "Report generated from saved construction analytics result.",
            },
            "kpis": {
                "planned_execution": premium_kpis.get("planned_progress_percent", metrics.get("planned_progress")),
                "actual_execution": premium_kpis.get("actual_progress_percent", metrics.get("actual_progress")),
                "schedule_gap_percent": premium_kpis.get("schedule_gap_percent", metrics.get("schedule_variance")),
                "delay_days": premium_kpis.get("delay_days", metrics.get("delay_days")),
                "total_cost": premium_kpis.get("contract_value", metrics.get("total_budget")),
                "planned_cost": metrics.get("planned_cost"),
                "actual_cost": premium_kpis.get("actual_cost", metrics.get("actual_cost")),
                "remaining_cost": premium_kpis.get("remaining_cost"),
                "cost_variance_amount": metrics.get("cost_variance"),
                "cost_variance_percent": premium_kpis.get("cost_variance_percent"),
                "workforce_current": premium_kpis.get("current_workforce"),
                "workforce_required": premium_kpis.get("required_workforce"),
                "risk_score": len([risk for risk in risks if risk.get("severity") in {"High", "Critical"}]) * 10,
                "risk_level": _highest_risk_level(risks),
                "currency": currency,
            },
            "forecast": {
                "baseline_finish": None,
                "estimated_finish": metrics.get("forecast_completion"),
                "delay_impact_days": metrics.get("delay_days"),
            },
            "dashboard_sections": {
                "primary_kpis": [
                    {"label": "CPI", "value": metrics.get("cpi"), "unit": "", "status": "neutral", "note": "Cost Performance Index"},
                    {"label": "SPI", "value": metrics.get("spi"), "unit": "", "status": "neutral", "note": "Schedule Performance Index"},
                    {"label": "Document completeness", "value": metrics.get("document_completeness_score"), "unit": "%", "status": "neutral", "note": "Document Control"},
                ] + _premium_primary_kpis(premium),
                "panels": _premium_panels(premium),
            },
            "premium_dashboard": premium,
            "executive_summary": summary,
            "risk_register": [
                {
                    "risk": risk.get("risk_title") or risk.get("title"),
                    "level": risk.get("severity"),
                    "reason": risk.get("explanation") or risk.get("description") or risk.get("impact"),
                    "action": risk.get("recommended_action") or risk.get("action"),
                }
                for risk in risks
            ],
            "recommended_actions": [item.get("action") for item in premium.get("recovery_actions", []) if item.get("action")] if premium else [risk.get("recommended_action") or risk.get("action") for risk in risks if risk.get("recommended_action") or risk.get("action")],
            "data_quality": {
                "confidence": analysis_result.get("confidence_score") or 0,
                "premium": premium.get("data_quality"),
                "warnings": (analysis_result.get("normalized_data") or {}).get("warnings") or [],
                "sheet_profiles": ((analysis_result.get("normalized_data") or {}).get("evidence") or {}).get("sheet_profiles") or [],
            },
            "analysis_provenance": analysis_result.get("input_manifest") or ((analysis_result.get("normalized_data") or {}).get("analysis_provenance")) or dashboard_data.get("analysis_provenance") or {},
        },
    }


def _premium_summary_text(premium: Dict[str, Any]) -> str:
    summary = premium.get("executive_summary") or {}
    parts = [
        summary.get("overall_project_status"),
        summary.get("main_delay_issue"),
        summary.get("main_cost_issue"),
        summary.get("main_material_issue"),
        summary.get("main_risk_issue"),
        summary.get("recommended_next_decision"),
    ]
    return " ".join(str(part) for part in parts if part not in (None, ""))


def _premium_primary_kpis(premium: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not premium:
        return []
    kpis = premium.get("kpis") or {}
    rows = [
        ("Project status", kpis.get("project_status"), "", "Executive Summary"),
        ("Planned progress", kpis.get("planned_progress_percent"), "%", "Schedule Analysis"),
        ("Actual progress", kpis.get("actual_progress_percent"), "%", "Schedule Analysis"),
        ("Delay days", kpis.get("delay_days"), "days", "Schedule Analysis"),
        ("Contract value", kpis.get("contract_value"), kpis.get("currency"), "KPI Summary"),
        ("Actual cost", kpis.get("actual_cost"), kpis.get("currency"), "Cost & Payment Analysis"),
        ("Approved payment", kpis.get("approved_payment"), kpis.get("currency"), "Cost & Payment Analysis"),
        ("Critical low-stock items", kpis.get("critical_low_stock_items"), "", "Material Continuity"),
        ("Top risks", kpis.get("top_risk_count"), "", "Risk Register"),
    ]
    return [{"label": label, "value": value, "unit": unit or "", "status": "neutral", "note": note} for label, value, unit, note in rows if value not in (None, "")]


def _premium_panels(premium: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not premium:
        return []
    panels: List[Dict[str, Any]] = []
    for title, section in [
        ("Executive Summary", premium.get("executive_summary") or {}),
        ("Schedule Analysis", premium.get("schedule_analysis") or {}),
        ("Cost & Payment Analysis", premium.get("cost_payment_analysis") or {}),
        ("Workforce Analysis", premium.get("workforce_analysis") or {}),
        ("Material Continuity", premium.get("material_continuity") or {}),
        ("Risk Register", premium.get("risk_register_analysis") or {}),
        ("Data Quality", premium.get("data_quality") or {}),
    ]:
        rows = []
        for key, value in section.items():
            if isinstance(value, (dict, list)):
                continue
            rows.append({"label": key.replace("_", " ").title(), "value": value, "unit": "", "status": "neutral"})
        if rows:
            panels.append({"title": title, "rows": rows[:10]})
    actions = premium.get("recovery_actions") or []
    if actions:
        panels.append({"title": "Recovery Actions", "rows": [{"label": item.get("module"), "value": item.get("action"), "unit": "", "status": item.get("priority")} for item in actions]})
    return panels


def _insert_report_row(
    user: CurrentUser,
    project: Dict[str, Any],
    project_id: str,
    result: Dict[str, Any],
    report_name: str,
    report_type: str,
    fmt: str,
    storage_path: str | None,
    media_type: str,
    report_payload: Dict[str, Any],
    payload_sha256: str,
    content_sha256: str,
) -> Dict[str, Any]:
    generated_at = datetime.utcnow().isoformat()
    payload = {
        "user_id": _user_uuid(user),
        "project_id": _project_db_id(project, project_id),
        "analysis_result_id": result.get("id") if uuid_like(str(result.get("id") or "")) else None,
        "owner_email": user.email,
        "report_name": report_name,
        "report_type": report_type,
        "format": fmt,
        "media_type": media_type,
        "storage_path": storage_path,
        "report_payload": report_payload,
        "payload_sha256": payload_sha256,
        "content_sha256": content_sha256,
        "snapshot_version": REPORT_SNAPSHOT_VERSION,
        "generated_at": generated_at,
        "download_count": 0,
        "status": "ready",
        "created_at": generated_at,
        "updated_at": generated_at,
    }
    if is_configured():
        try:
            return insert_row("reports", payload)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Report archive could not be saved."}) from exc
    if local_store_enabled():
        from ..saas_ids import make_public_id
        from ..saas_store import insert

        return insert("reports", {**payload, "id": make_public_id("report"), "report_id": make_public_id("report"), "project_id": project_id})
    raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Report archive requires Supabase PostgreSQL or explicit local fallback."})

def normalize_report_format(value: Any) -> str:
    normalized = str(value or "pdf").strip().lower()
    aliases = {"pdf": "pdf", "xlsx": "excel", "excel": "excel"}
    if normalized not in aliases:
        raise HTTPException(
            status_code=422,
            detail={"error": "unsupported_report_format", "message": "report_format must be one of: pdf, excel, xlsx."},
        )
    return aliases[normalized]


def normalize_report_type(value: Any) -> str:
    normalized = " ".join(str(value or "Project Control Report").split())
    if not normalized:
        normalized = "Project Control Report"
    if len(normalized) > 120:
        raise HTTPException(status_code=422, detail={"error": "invalid_report_type", "message": "report_type must not exceed 120 characters."})
    return normalized


def _canonical_payload_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _payload_sha256(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()


def _content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _record_report_download(report: Dict[str, Any], user: CurrentUser) -> None:
    """Best-effort audit increment after authorization and file generation.

    The DB RPC increments the counter atomically. A failure to write telemetry
    must not turn an otherwise valid report download into an error.
    """
    report_db_id = str(report.get("id") or "")
    if is_configured() and uuid_like(report_db_id):
        try:
            call_rpc("record_report_download", {"p_report_id": report_db_id})
        except ProductionStoreError:
            return
        return
    if local_store_enabled():
        from ..saas_store import update_one

        key = "id" if report.get("id") else "report_id"
        value = str(report.get(key) or "")
        if not value:
            return
        now = datetime.utcnow().isoformat()
        update_one(
            "reports",
            key,
            value,
            {
                "download_count": int(report.get("download_count") or 0) + 1,
                "last_downloaded_at": now,
            },
        )


def _find_report(report_id: str) -> Dict[str, Any] | None:
    if is_configured():
        filters = [{"id": report_id}] if uuid_like(report_id) else [{"report_id": report_id}]
        return first_existing("reports", filters)
    if local_store_enabled():
        from ..saas_store import find_one

        return find_one("reports", id=report_id) or find_one("reports", report_id=report_id)
    return None


def _find_project_for_report(report: Dict[str, Any]) -> Dict[str, Any] | None:
    project_id = str(report.get("project_id") or "")
    if is_configured() and uuid_like(project_id):
        return first_existing("projects", [{"id": project_id}])
    if local_store_enabled():
        from ..saas_store import find_one

        return find_one("projects", project_id=project_id)
    return None


def _find_result_for_report(report: Dict[str, Any]) -> Dict[str, Any] | None:
    result_id = str(report.get("analysis_result_id") or "")
    if is_configured() and uuid_like(result_id):
        return first_existing("analysis_results", [{"id": result_id}])
    if is_configured() and uuid_like(str(report.get("project_id") or "")):
        rows = select_rows("analysis_results", {"project_id": report.get("project_id")}, limit=50)
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[0] if rows else None
    if local_store_enabled():
        from ..saas_store import find_one, list_rows

        direct = find_one("analysis_results", id=result_id) or find_one("analysis_results", analysis_id=result_id)
        if direct:
            return direct
        rows = list_rows("analysis_results", project_id=report.get("project_id"))
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[0] if rows else None
    return None


def _store_local_report(content: bytes, project_id: str, extension: str) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{project_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{extension}"
    path.write_bytes(content)
    return str(path)


def _report_api(row: Dict[str, Any], project: Dict[str, Any]) -> Dict[str, Any]:
    report_id = row.get("id") or row.get("report_id")
    payload = row.get("report_payload")
    snapshot_available = isinstance(payload, dict) and bool(payload)
    return {
        "id": report_id,
        "report_id": row.get("report_id") or report_id,
        "report_name": row.get("report_name") or row.get("name") or "Project Control Report",
        "name": row.get("report_name") or row.get("name") or "Project Control Report",
        "project_name": project.get("project_name") or row.get("project_name"),
        "project": project.get("project_name") or row.get("project_name") or "Project",
        "report_type": row.get("report_type") or "Project Control Report",
        "type": row.get("report_type") or "Project Control",
        "created_date": row.get("created_at"),
        "created": row.get("created_at"),
        "generated_at": row.get("generated_at") or row.get("created_at"),
        "format": str(row.get("format") or "PDF").upper(),
        "status": row.get("status") or "ready",
        "snapshot_version": row.get("snapshot_version") or (REPORT_SNAPSHOT_VERSION if snapshot_available else None),
        "snapshot_available": snapshot_available,
        "payload_sha256": row.get("payload_sha256"),
        "content_sha256": row.get("content_sha256"),
        "download_count": int(row.get("download_count") or 0),
        "last_downloaded_at": row.get("last_downloaded_at"),
        "download_path": f"/api/reports/{report_id}/download" if report_id else None,
    }

def _report_project_access_allowed(project: Dict[str, Any], user: CurrentUser) -> bool:
    if is_staff_role(user.role):
        return can_access_project_scope(user.role, "reports")
    try:
        return can_access_project_resource(project, user, "reports")
    except ProductionStoreError:
        return False


def _row_belongs_to_user(row: Dict[str, Any], user: CurrentUser) -> bool:
    # Report downloads expose customer project findings, so staff need the
    # explicit reports permission rather than a broad staff bypass.
    if is_staff_role(user.role):
        return can_access_project_scope(user.role, "reports")
    values = {str(row.get("user_id") or "").lower(), str(row.get("owner_email") or "").lower()}
    return bool(values.intersection({str(user.id).lower(), str(user.auth_user_id).lower(), str(user.email).lower()}))


def _project_db_id(project: Dict[str, Any], requested_project_id: str) -> str | None:
    if uuid_like(str(project.get("id") or "")):
        return str(project.get("id"))
    if uuid_like(str(requested_project_id or "")):
        return str(requested_project_id)
    return None


def _user_uuid(user: CurrentUser) -> str | None:
    if uuid_like(user.id):
        return user.id
    if uuid_like(user.auth_user_id):
        return user.auth_user_id
    return None


def _safe_filename(name: str, extension: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(name or "DevBareun_Report"))
    return f"{safe[:120]}.{extension}"


def _summary_text(dashboard_data: Dict[str, Any], risks: List[Dict[str, Any]]) -> str:
    metrics = dashboard_data.get("metrics") or {}
    high = [risk for risk in risks if risk.get("severity") in {"High", "Critical"}]
    cpi = metrics.get("cpi")
    spi = metrics.get("spi")
    return (
        f"Project performance review completed with CPI {cpi if cpi is not None else 'not available'} "
        f"and SPI {spi if spi is not None else 'not available'}. "
        f"{len(high)} high-priority risk items require management attention."
    )


def _highest_risk_level(risks: List[Dict[str, Any]]) -> str:
    order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    if not risks:
        return "Low"
    return max((risk.get("severity") or "Low" for risk in risks), key=lambda item: order.get(item, 0))
