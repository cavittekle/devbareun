"""Project-scoped collaboration activity API."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .production_store import ProductionStoreError
from .services.project_activity_service import list_project_activity

router = APIRouter(prefix="/api/project-activity", tags=["project activity"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail={"error": "forbidden", "message": str(exc)})
    if isinstance(exc, ProductionStoreError):
        return HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project activity is unavailable."})
    return HTTPException(status_code=500, detail={"error": "project_activity_failed", "message": "Project activity could not be loaded."})


@router.get("/{project_id}")
async def project_activity_timeline(
    project_id: str,
    limit: int = Query(default=80, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="project_activity")
    try:
        events = list_project_activity(project, current_user, limit=limit)
    except Exception as exc:
        raise _error(exc) from exc
    return {"project_id": project_id, "events": events}
