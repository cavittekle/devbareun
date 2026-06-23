from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .services.analysis_job_service import get_latest_analysis_result, list_user_projects, list_user_results
from .services.dashboard_service import build_executive_dashboard, build_portfolio_dashboard


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/portfolio")
async def portfolio_dashboard(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    projects = list_user_projects(current_user)
    results = list_user_results(current_user)
    return build_portfolio_dashboard(projects=projects, analysis_results=results)


@router.get("/executive/{project_id}")
async def executive_dashboard(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="dashboard")
    result = get_latest_analysis_result(project_id, project, current_user)
    projects = list_user_projects(current_user)
    return build_executive_dashboard(project=project, analysis_result=result, projects=projects)

