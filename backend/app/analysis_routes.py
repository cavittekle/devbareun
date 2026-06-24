from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner, require_staff_permission
from .services.project_activity_service import record_project_activity
from .services.analysis_job_service import (
    analysis_operations_status,
    create_analysis_job,
    get_analysis_job,
    get_latest_analysis_result,
    list_analysis_recovery_jobs,
    requeue_analysis_job,
)


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class StartAnalysisRequest(BaseModel):
    analysis_type: str = Field(default="all", max_length=40)


class RecoverAnalysisJobRequest(BaseModel):
    reset_attempts: bool = False


def _require_staff_operations(current_user: CurrentUser) -> None:
    # Queue state and manual retry can affect every tenant. They are reserved
    # for owner/operator roles, not all staff accounts.
    require_staff_permission(current_user, "operations")


@router.post("/start/{project_id}")
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    payload: StartAnalysisRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="projects")
    analysis_type = (payload.analysis_type if payload else "all") or "all"
    response = create_analysis_job(
        project_id=project_id,
        project=project,
        user=current_user,
        background_tasks=background_tasks,
        analysis_type=analysis_type,
        idempotency_key=idempotency_key,
    )
    if not response.get("idempotent_replay") and not response.get("active_job_reused"):
        try:
            record_project_activity(
                project,
                current_user,
                "analysis.queued",
                "analysis_job",
                str(response.get("job_id") or response.get("id") or "") or None,
                {"analysis_type": analysis_type, "status": response.get("status") or "queued"},
            )
        except Exception:
            pass
    return response


@router.get("/jobs/{job_id}")
async def analysis_job(job_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return get_analysis_job(job_id, current_user)


@router.get("/results/{project_id}")
async def analysis_results(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="projects")
    result = get_latest_analysis_result(project_id, project, current_user)
    return {"project_id": project_id, "analysis_result": result}



@router.get("/operations")
async def analysis_operations(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Operational queue/worker state, available only to staff roles."""
    _require_staff_operations(current_user)
    return analysis_operations_status()


@router.get("/operations/recovery-jobs")
async def analysis_recovery_jobs(limit: int = 50, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    """List failed/dead-letter jobs using staff-safe metadata only."""
    _require_staff_operations(current_user)
    return {"jobs": list_analysis_recovery_jobs(limit=limit)}


@router.post("/operations/jobs/{job_id}/retry")
async def retry_analysis_job(
    job_id: str,
    payload: RecoverAnalysisJobRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Explicit staff recovery; dead-letter jobs require reset_attempts=true."""
    _require_staff_operations(current_user)
    return requeue_analysis_job(job_id=job_id, actor=current_user, reset_attempts=bool(payload.reset_attempts if payload else False))
