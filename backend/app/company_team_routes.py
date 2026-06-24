"""Authenticated company workspace and controlled team invitation routes."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .auth_dependencies import CurrentUser, get_current_user
from .services import audit_service
from .services.company_team_service import (
    accept_invitation,
    bootstrap_workspace,
    company_team_payload,
    create_invitation,
    revoke_invitation,
    update_member,
)
from .production_store import ProductionStoreError

router = APIRouter(prefix="/api/company", tags=["company workspace"])


class WorkspaceBootstrapRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=180)


class CompanyInviteRequest(BaseModel):
    email: EmailStr
    company_role: str = Field(pattern="^(manager|editor|viewer)$")
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=168)


class InviteAcceptRequest(BaseModel):
    token: str = Field(min_length=24, max_length=512)


class CompanyMemberUpdateRequest(BaseModel):
    company_role: Optional[str] = Field(default=None, pattern="^(manager|editor|viewer)$")
    status: Optional[str] = Field(default=None, pattern="^(active|suspended)$")


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail={"error": "not_found", "message": str(exc)})
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail={"error": "forbidden", "message": str(exc)})
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail={"error": "invalid_team_request", "message": str(exc)})
    if isinstance(exc, ProductionStoreError):
        return HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Company workspace data is unavailable."})
    return HTTPException(status_code=500, detail={"error": "company_workspace_failed", "message": "Company workspace action could not be completed."})


def _audit(actor: CurrentUser, action: str, entity_type: str, entity_id: str | None = None, metadata: Dict[str, Any] | None = None) -> None:
    try:
        audit_service.record_audit_event(
            actor.payload(),
            action,
            entity_type,
            entity_id,
            metadata or {},
        )
    except Exception:
        # Audit delivery must not convert a successful company action into a
        # client-visible failure. Existing audit outbox/retry handles the event.
        return


def _email_fingerprint(value: str | None) -> str:
    return hashlib.sha256(str(value or "").strip().lower().encode("utf-8")).hexdigest()


@router.get("/workspace")
async def company_workspace(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        return company_team_payload(current_user)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/workspace")
async def create_company_workspace(
    payload: WorkspaceBootstrapRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        company, membership, created = bootstrap_workspace(current_user, payload.company_name)
        result = company_team_payload(current_user)
        result["created"] = bool(created)
        _audit(
            current_user,
            "company.workspace.created" if created else "company.workspace.reused",
            "company_workspace",
            str(company.get("id") or "") or None,
            {"membership_id": str(membership.get("id") or "")},
        )
        return result
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/invitations")
async def invite_company_member(
    payload: CompanyInviteRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        result = create_invitation(
            current_user,
            str(payload.email),
            payload.company_role,
            payload.expires_in_hours,
        )
        invitation = result.get("invitation") or {}
        _audit(
            current_user,
            "company.invitation.created",
            "company_invitation",
            str(invitation.get("invitation_id") or "") or None,
            {
                "company_role": invitation.get("company_role"),
                "invitee_email_sha256": _email_fingerprint(invitation.get("invitee_email")),
            },
        )
        return result
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/invitations/accept")
async def accept_company_invitation(
    payload: InviteAcceptRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        company, membership = accept_invitation(current_user, payload.token)
        _audit(
            current_user,
            "company.invitation.accepted",
            "company_membership",
            str(membership.get("id") or "") or None,
            {"company_id": str(company.get("id") or "")},
        )
        return company_team_payload(current_user)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/invitations/{invitation_id}/revoke")
async def revoke_company_invitation(
    invitation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        invitation = revoke_invitation(current_user, invitation_id)
        _audit(current_user, "company.invitation.revoked", "company_invitation", invitation_id)
        return {"invitation": {
            "invitation_id": str(invitation.get("id") or invitation_id),
            "status": invitation.get("status") or "revoked",
        }}
    except Exception as exc:
        raise _error(exc) from exc


@router.patch("/members/{membership_id}")
async def update_company_member(
    membership_id: str,
    payload: CompanyMemberUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        member = update_member(
            current_user,
            membership_id,
            role=payload.company_role,
            status=payload.status,
        )
        _audit(
            current_user,
            "company.member.updated",
            "company_membership",
            membership_id,
            {"company_role": member.get("company_role"), "status": member.get("status")},
        )
        return {"member": {
            "membership_id": str(member.get("id") or membership_id),
            "company_role": member.get("company_role"),
            "status": member.get("status"),
        }}
    except Exception as exc:
        raise _error(exc) from exc
