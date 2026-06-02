from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .services.analysis_job_service import create_analysis_job, get_analysis_job, get_latest_analysis_result


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class StartAnalysisRequest(BaseModel):
    analysis_type: str = Field(default="all", max_length=40)


@router.post("/start/{project_id}")
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    payload: StartAnalysisRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user)
    analysis_type = (payload.analysis_type if payload else "all") or "all"
    return create_analysis_job(
        project_id=project_id,
        project=project,
        user=current_user,
        background_tasks=background_tasks,
        analysis_type=analysis_type,
    )


@router.get("/jobs/{job_id}")
async def analysis_job(job_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return get_analysis_job(job_id, current_user)


@router.get("/results/{project_id}")
async def analysis_results(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user)
    result = get_latest_analysis_result(project_id, project, current_user)
    return {"project_id": project_id, "analysis_result": result}

