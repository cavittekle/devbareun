"""Project sharing API for explicit company-member grants."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .production_store import ProductionStoreError
from .services.audit_service import record_audit_event
from .services.project_activity_service import record_project_activity
from .services.project_sharing_service import (
    grant_project_access,
    list_accessible_projects,
    list_project_access,
    revoke_project_access,
    update_project_access,
)

router = APIRouter(prefix="/api/project-access", tags=["project access"])


class ProjectAccessGrantRequest(BaseModel):
    membership_id: str = Field(min_length=1, max_length=80)
    project_role: str = Field(pattern="^(manager|editor|viewer)$")


class ProjectAccessUpdateRequest(BaseModel):
    project_role: str | None = Field(default=None, pattern="^(manager|editor|viewer)$")
    status: str | None = Field(default=None, pattern="^(active|revoked)$")


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail={"error": "forbidden", "message": str(exc)})
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail={"error": "not_found", "message": str(exc)})
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail={"error": "invalid_project_access", "message": str(exc)})
    if isinstance(exc, ProductionStoreError):
        return HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project access could not be updated."})
    return HTTPException(status_code=500, detail={"error": "project_access_failed", "message": "Project access operation could not be completed."})


def _audit(actor: CurrentUser, action: str, project_id: str, metadata: Dict[str, Any], project: Dict[str, Any] | None = None) -> None:
    try:
        record_audit_event(
            actor=actor.payload(),
            action=action,
            entity_type="project_access_grant",
            entity_id=project_id,
            metadata=metadata,
            require_durable=False,
        )
    except Exception:
        pass
    if project:
        try:
            record_project_activity(
                project,
                actor,
                action,
                "project_access_grant",
                str(metadata.get("grant_id") or metadata.get("membership_id") or "") or None,
                metadata,
            )
        except Exception:
            pass


@router.get("/projects")
async def accessible_projects(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        rows = list_accessible_projects(current_user)
    except ProductionStoreError as exc:
        raise _error(exc) from exc
    return {"projects": rows}


@router.get("/{project_id}/members")
async def project_access_members(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="project_access_manage")
    try:
        grants = list_project_access(project, current_user)
    except Exception as exc:
        raise _error(exc) from exc
    return {"project_id": project_id, "grants": grants}


@router.post("/{project_id}/members")
async def create_project_access_grant(
    project_id: str,
    payload: ProjectAccessGrantRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="project_access_manage")
    try:
        grant = grant_project_access(project, current_user, membership_id=payload.membership_id, project_role=payload.project_role)
    except Exception as exc:
        raise _error(exc) from exc
    _audit(current_user, "project_access.granted", project_id, {"membership_id": payload.membership_id, "grant_id": grant.get("grant_id"), "project_role": grant.get("project_role")}, project)
    return {"grant": grant}


@router.patch("/{project_id}/members/{grant_id}")
async def patch_project_access_grant(
    project_id: str,
    grant_id: str,
    payload: ProjectAccessUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="project_access_manage")
    try:
        grant = update_project_access(project, current_user, grant_id=grant_id, project_role=payload.project_role, status=payload.status)
    except Exception as exc:
        raise _error(exc) from exc
    _audit(current_user, "project_access.updated", project_id, {"grant_id": grant_id, "project_role": grant.get("project_role"), "status": grant.get("status")}, project)
    return {"grant": grant}


@router.delete("/{project_id}/members/{grant_id}")
async def delete_project_access_grant(
    project_id: str,
    grant_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="project_access_manage")
    try:
        grant = revoke_project_access(project, current_user, grant_id=grant_id)
    except Exception as exc:
        raise _error(exc) from exc
    _audit(current_user, "project_access.revoked", project_id, {"grant_id": grant_id}, project)
    return {"grant": grant}
