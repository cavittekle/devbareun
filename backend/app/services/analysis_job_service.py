from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException

from ..auth_dependencies import CurrentUser, local_store_enabled
from ..analysis_types import normalize_analysis_type
from ..production_store import ProductionStoreError, first_existing, first_update, insert_row, is_configured, select_rows, uuid_like
from ..security_runtime import production_security_enabled
from .analytics_service import build_analytics
from .billing_service import consume_after_success, ensure_analysis_available
from .parser_service import parse_project_files
from .premium_analysis import analyze_full_project_control_premium
from .risk_engine import generate_risk_register


JOB_STATUSES = {"queued", "running", "completed", "failed"}


def create_analysis_job(
    *,
    project_id: str,
    project: Dict[str, Any],
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    analysis_type: str = "all",
) -> Dict[str, Any]:
    analysis_type = normalize_analysis_type(analysis_type)
    ensure_analysis_available(user, project_id)
    files = list_project_files_for_analysis(project_id, project)
    if not files:
        raise HTTPException(status_code=400, detail={"error": "no_uploaded_files", "message": "Upload project files before starting project review."})

    if not is_configured():
        if local_store_enabled():
            return _create_local_job(project_id, user, files, analysis_type, background_tasks, project)
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Supabase PostgreSQL is required for background analysis jobs."})
        raise HTTPException(status_code=503, detail={"error": "local_store_disabled", "message": "Enable DEVBAREUN_ENABLE_LOCAL_STORE=true for local development fallback."})

    db_project_id = _project_db_id(project, project_id)
    payload = {
        "user_id": _user_uuid(user),
        "project_id": db_project_id,
        "owner_email": user.email,
        "analysis_type": analysis_type,
        "status": "queued",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        job = insert_row("analysis_jobs", payload)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Analysis job could not be created."}) from exc

    job_id = str(job.get("id"))
    background_tasks.add_task(run_analysis_job, job_id=job_id, project_id=project_id, user_payload=user.payload(), analysis_type=analysis_type)
    return {"job_id": job_id, "status": "queued", "message": "Analysis job created"}


def run_analysis_job(*, job_id: str, project_id: str, user_payload: Dict[str, Any], analysis_type: str = "all") -> None:
    analysis_type = normalize_analysis_type(analysis_type)
    user = CurrentUser(**user_payload)
    try:
        _update_job(job_id, {"status": "running", "progress": 15, "started_at": datetime.utcnow().isoformat(), "error_message": None})
        project = _load_project_for_job(project_id)
        files = list_project_files_for_analysis(project_id, project)
        if not files:
            raise RuntimeError("No uploaded project files were found.")

        _update_job(job_id, {"progress": 35})
        normalized = parse_project_files(files, analysis_type=analysis_type, project=project)
        _update_job(job_id, {"progress": 58})
        analytics = build_analytics(normalized, project)
        risks = generate_risk_register(normalized, analytics)
        analytics.setdefault("metrics", {})["high_risk_count"] = len([risk for risk in risks if risk.get("severity") in {"High", "Critical"}])
        premium_dashboard = analyze_full_project_control_premium(normalized, analytics, risks)
        analytics["analysis_type"] = premium_dashboard["analysis_type"]
        analytics["premium_dashboard"] = premium_dashboard
        _update_job(job_id, {"progress": 78})
        result = _save_result(user, project, project_id, job_id, normalized, analytics, risks)
        _save_risks(user, project, project_id, result, risks)
        consume_after_success(user, project_id, job_id)
        _mark_files_parsed(files)
        _update_job(job_id, {"status": "completed", "progress": 100, "completed_at": datetime.utcnow().isoformat()})
    except Exception as exc:
        _update_job(job_id, {"status": "failed", "progress": 100, "error_message": _safe_error(exc), "completed_at": datetime.utcnow().isoformat()})


def get_analysis_job(job_id: str, user: CurrentUser) -> Dict[str, Any]:
    job = _find_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Analysis job was not found."})
    if not _row_belongs_to_user(job, user):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can access only your own analysis job."})
    return {"job": job}


def get_latest_analysis_result(project_id: str, project: Dict[str, Any], user: CurrentUser) -> Dict[str, Any] | None:
    db_project_id = _project_db_id(project, project_id)
    rows: List[Dict[str, Any]] = []
    if is_configured() and db_project_id:
        rows = select_rows("analysis_results", {"project_id": db_project_id}, limit=100)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("analysis_results", project_id=project_id)
    rows = [row for row in rows if _row_belongs_to_user(row, user)]
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows[0] if rows else None


def list_project_files_for_analysis(project_id: str, project: Dict[str, Any]) -> List[Dict[str, Any]]:
    db_project_id = _project_db_id(project, project_id)
    if is_configured() and db_project_id:
        rows = select_rows("uploaded_files", {"project_id": db_project_id}, limit=500)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("uploaded_files", project_id=project_id)
    else:
        rows = []
    return [
        row for row in rows
        if str(row.get("upload_status") or row.get("status") or "").lower() in {"uploaded", "metadata_recorded", "parsed", "approved", "local_metadata_only"}
        and not row.get("deleted_at")
    ]


def list_user_projects(user: CurrentUser) -> List[Dict[str, Any]]:
    if is_configured():
        return select_rows("projects", {"owner_email": user.email}, limit=500)
    if local_store_enabled():
        from ..saas_store import list_rows

        return list_rows("projects", owner_email=user.email)
    return []


def list_user_results(user: CurrentUser) -> List[Dict[str, Any]]:
    if is_configured():
        return select_rows("analysis_results", {"owner_email": user.email}, limit=500)
    if local_store_enabled():
        from ..saas_store import list_rows

        return list_rows("analysis_results", owner_email=user.email)
    return []


def _create_local_job(
    project_id: str,
    user: CurrentUser,
    files: List[Dict[str, Any]],
    analysis_type: str,
    background_tasks: BackgroundTasks,
    project: Dict[str, Any],
) -> Dict[str, Any]:
    from ..saas_ids import make_public_id
    from ..saas_store import insert

    job_id = make_public_id("analysis").replace("DB-ANL", "DB-JOB")
    insert("analysis_jobs", {
        "id": job_id,
        "job_id": job_id,
        "project_id": project_id,
        "owner_email": user.email,
        "analysis_type": analysis_type,
        "status": "queued",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
    })
    background_tasks.add_task(run_analysis_job, job_id=job_id, project_id=project_id, user_payload=user.payload(), analysis_type=analysis_type)
    return {"job_id": job_id, "status": "queued", "message": "Analysis job created"}


def _load_project_for_job(project_id: str) -> Dict[str, Any]:
    if is_configured():
        project = first_existing("projects", _project_filters(project_id))
        if not project:
            raise RuntimeError("Project was not found.")
        return project
    if local_store_enabled():
        from ..saas_store import find_one

        project = find_one("projects", project_id=project_id)
        if not project:
            raise RuntimeError("Project was not found.")
        return project
    raise RuntimeError("Database is not configured.")


def _save_result(
    user: CurrentUser,
    project: Dict[str, Any],
    project_id: str,
    job_id: str,
    normalized: Dict[str, Any],
    analytics: Dict[str, Any],
    risks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if is_configured():
        return insert_row("analysis_results", {
            "user_id": _user_uuid(user),
            "project_id": _project_db_id(project, project_id),
            "job_id": job_id if uuid_like(job_id) else None,
            "owner_email": user.email,
            "normalized_data": normalized,
            "dashboard_data": analytics,
            "risk_data": risks,
            "confidence_score": normalized.get("confidence_score") or 0,
            "analysis_type": (normalized.get("project_info") or {}).get("analysis_type") or "all",
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
        })
    if local_store_enabled():
        from ..saas_ids import make_public_id
        from ..saas_store import insert

        return insert("analysis_results", {
            "id": make_public_id("analysis"),
            "analysis_id": make_public_id("analysis"),
            "project_id": project_id,
            "job_id": job_id,
            "owner_email": user.email,
            "normalized_data": normalized,
            "dashboard_data": analytics,
            "risk_data": risks,
            "confidence_score": normalized.get("confidence_score") or 0,
            "analysis_type": (normalized.get("project_info") or {}).get("analysis_type") or "all",
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
        })
    raise RuntimeError("Database is not configured.")


def _save_risks(user: CurrentUser, project: Dict[str, Any], project_id: str, result: Dict[str, Any], risks: List[Dict[str, Any]]) -> None:
    if not is_configured():
        return
    for risk in risks:
        try:
            insert_row("risks", {
                "user_id": _user_uuid(user),
                "project_id": _project_db_id(project, project_id),
                "analysis_result_id": result.get("id") if uuid_like(str(result.get("id") or "")) else None,
                "risk_title": risk.get("risk_title") or risk.get("title") or "Project risk",
                "category": risk.get("category"),
                "severity": risk.get("severity"),
                "probability": risk.get("probability"),
                "impact": risk.get("impact"),
                "explanation": risk.get("explanation") or risk.get("description"),
                "recommended_action": risk.get("recommended_action") or risk.get("action"),
                "status": risk.get("status") or "Open",
                "created_at": datetime.utcnow().isoformat(),
            })
        except ProductionStoreError:
            continue


def _mark_files_parsed(files: List[Dict[str, Any]]) -> None:
    if not is_configured():
        return
    for row in files:
        row_id = row.get("id")
        if row_id:
            try:
                first_update("uploaded_files", {"id": row_id}, {"parser_status": "parsed", "updated_at": datetime.utcnow().isoformat()})
            except ProductionStoreError:
                continue


def _find_job(job_id: str) -> Optional[Dict[str, Any]]:
    if is_configured():
        if uuid_like(job_id):
            return first_existing("analysis_jobs", [{"id": job_id}])
        return None
    if local_store_enabled():
        from ..saas_store import find_one

        return find_one("analysis_jobs", job_id=job_id) or find_one("analysis_jobs", id=job_id)
    return None


def _update_job(job_id: str, patch: Dict[str, Any]) -> None:
    if is_configured():
        try:
            if uuid_like(job_id):
                first_update("analysis_jobs", {"id": job_id}, patch)
        except ProductionStoreError:
            return
    elif local_store_enabled():
        from ..saas_store import update_one

        update_one("analysis_jobs", "job_id", job_id, patch) or update_one("analysis_jobs", "id", job_id, patch)


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


def _project_filters(project_id: str) -> List[Dict[str, Any]]:
    filters: List[Dict[str, Any]] = []
    if uuid_like(project_id):
        filters.append({"id": project_id})
    filters.append({"project_id": project_id})
    return filters


def _row_belongs_to_user(row: Dict[str, Any], user: CurrentUser) -> bool:
    if user.is_admin:
        return True
    values = {
        str(row.get("user_id") or "").lower(),
        str(row.get("owner_email") or "").lower(),
        str(row.get("uploaded_by_user_id") or "").lower(),
    }
    candidates = {str(user.id).lower(), str(user.auth_user_id).lower(), str(user.email).lower()}
    return bool(values.intersection(candidates))


def _safe_error(exc: Exception) -> str:
    if production_security_enabled():
        return "Analysis job failed. Please review uploaded files and try again."
    text = str(exc) or exc.__class__.__name__
    blocked = ["SUPABASE_SERVICE_ROLE_KEY", "LEMON_SQUEEZY_API_KEY", "LEMON_SQUEEZY_WEBHOOK_SECRET", "Authorization", "Bearer "]
    for item in blocked:
        text = text.replace(item, "[redacted]")
    return text[:500]
