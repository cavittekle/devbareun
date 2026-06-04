
"""
DevBareun Persistence Routes
v1.3.8 — Persistent Analysis + Report Archive + Billing Entitlements
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .auth_runtime import verify_supabase_token, get_bearer_token, AuthError, auth_user_payload, plan_credit_limit
from .persistence_runtime import (
    save_project,
    list_projects,
    save_analysis,
    get_analysis,
    list_analyses,
    save_report_archive,
    list_report_archive,
    get_report_archive,
    create_guest_result,
    get_guest_result,
)
from .saas_credits import credit_summary
from .security_runtime import safe_guest_ttl_days, validate_public_token


router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class ProjectCreateRequest(BaseModel):
    project_name: str
    location: Optional[str] = None
    contractor: Optional[str] = None
    client: Optional[str] = None
    contract_value: Optional[float] = None
    currency: Optional[str] = "AZN"
    status: Optional[str] = "active"


class AnalysisSaveRequest(BaseModel):
    project_id: str
    analysis_type: Optional[str] = "all"
    file_ids: Optional[list[str]] = []
    dashboard: Dict[str, Any] = {}
    kpis: Dict[str, Any] = {}
    report_payload: Dict[str, Any] = {}
    result_id: Optional[str] = None
    status: Optional[str] = "completed"


class ReportArchiveRequest(BaseModel):
    analysis_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    analysis_type: Optional[str] = "all"
    report_type: Optional[str] = "dashboard"
    language: Optional[str] = "en"
    print_size: Optional[str] = "A4"
    print_orientation: Optional[str] = None
    title: Optional[str] = None
    dashboard: Dict[str, Any] = {}
    kpis: Dict[str, Any] = {}
    report_payload: Dict[str, Any] = {}
    status: Optional[str] = "archived"


class GuestResultRequest(BaseModel):
    email: str
    project_name: Optional[str] = None
    analysis_id: Optional[str] = None
    dashboard: Dict[str, Any] = {}
    ttl_days: Optional[int] = 14


async def require_user(authorization: Optional[str]):
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    try:
        return await verify_supabase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/entitlements")
async def entitlements(authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    projects_list = await list_projects(user.email)
    analyses_list = await list_analyses(user.email)
    reports_list = await list_report_archive(user.email)
    ledger = credit_summary(owner_email=user.email)
    session_remaining = int(user.credits_remaining or 0)
    ledger_remaining = int(ledger.get("remaining") or 0)
    effective_remaining = max(session_remaining, ledger_remaining)
    return {
        "user": auth_user_payload(user),
        "plan": user.plan,
        "plan_limit": plan_credit_limit(user.plan),
        "credits_remaining": effective_remaining,
        "credit_source": "ledger" if ledger_remaining >= session_remaining and ledger_remaining > 0 else "session",
        "ledger": ledger,
        "usage": {
            "projects": len(projects_list),
            "analyses": len(analyses_list),
            "reports": len(reports_list),
        },
        "features": {
            "saved_reports": True,
            "a4_print": True,
            "a3_print": user.plan in {"plus", "pro"} or effective_remaining > 0,
            "pdf_export": effective_remaining > 0 or bool(reports_list),
            "excel_export": user.plan in {"plus", "pro"},
        },
    }


@router.post("/projects")
async def create_project(payload: ProjectCreateRequest, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    record = await save_project(user.email, payload.dict())
    return {"project": record}


@router.get("/projects")
async def projects(authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    return {"projects": await list_projects(user.email)}


@router.post("/analysis/save")
async def save_analysis_result(payload: AnalysisSaveRequest, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    record = await save_analysis(user.email, payload.dict())
    return {"analysis": record}


@router.get("/analysis")
async def analyses(project_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    return {"analyses": await list_analyses(user.email, project_id=project_id)}


@router.get("/analysis/{analysis_id}")
async def analysis_detail(analysis_id: str, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    row = await get_analysis(user.email, analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {"analysis": row}


@router.post("/reports/archive")
async def archive_report(payload: ReportArchiveRequest, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    record = await save_report_archive(user.email, payload.dict())
    return {"report": record}


@router.get("/reports")
async def report_archive(project_id: Optional[str] = None, analysis_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    return {"reports": await list_report_archive(user.email, project_id=project_id, analysis_id=analysis_id)}


@router.get("/reports/{report_id}")
async def report_detail(report_id: str, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    row = await get_report_archive(user.email, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"report": row}


@router.post("/guest-results")
async def create_guest_result_route(payload: GuestResultRequest):
    record = await create_guest_result(payload.dict(), ttl_days=safe_guest_ttl_days(payload.ttl_days))
    return {
        "guest_result": record,
        "secure_url": f"/guest-result.html?token={record['guest_token']}",
    }


@router.get("/guest-results/{token}")
async def guest_result(token: str):
    token = validate_public_token(token, "guest result link")
    row = await get_guest_result(token)
    if not row:
        raise HTTPException(status_code=404, detail="Guest result not found or expired.")
    return {"guest_result": row}
