from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .services.report_service import generate_report, get_report_download, list_project_reports


router = APIRouter(prefix="/api/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    report_format: str = Field(default="pdf", max_length=20)
    report_type: str = Field(default="Full Project Control Report", max_length=120)


@router.get("/project/{project_id}")
async def project_reports(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user)
    return list_project_reports(project_id, project, current_user)


@router.post("/generate/{project_id}")
async def generate_project_report(
    project_id: str,
    payload: GenerateReportRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user)
    request = payload or GenerateReportRequest()
    return generate_report(project_id, project, current_user, request.report_format, request.report_type)


@router.get("/{report_id}/download")
async def download_report(report_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Response:
    content, media_type, filename = get_report_download(report_id, current_user)
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

