"""Customer privacy and data-retention request routes.

The endpoints create auditable lifecycle requests. They do not directly erase
Supabase Auth identities, invoices, immutable audit records, backups or private
storage objects. A later reviewed execution process must apply retention policy
with legal/accounting controls in place.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .audit_context import current_request_id
from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .production_store import ProductionStoreError, first_update, insert_row, is_configured, select_rows, uuid_like
from .saas_ids import make_public_id
from .saas_store import find_one, insert, list_rows, update_one
from .services.audit_service import record_audit_event
from .services.data_lifecycle_service import (
    ACTIVE_STATUSES,
    ERASURE_CONFIRMATION,
    REVIEW_STATUSES,
    admin_safe_row,
    customer_safe_row,
    is_active_request,
    policy_from_env,
    request_payload,
    row_owned_by,
    same_request_scope,
    validate_erasure_confirmation,
    validate_request_scope,
)

router = APIRouter(prefix="/api/privacy", tags=["Privacy & data lifecycle"])


class DataExportRequest(BaseModel):
    scope: str = Field(default="account", pattern="^(account|project)$")
    project_id: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=1000)


class DataErasureRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=120)
    scope: str = Field(default="account", pattern="^(account|project)$")
    project_id: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=1000)


class CancelDataLifecycleRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class DataLifecycleReviewRequest(BaseModel):
    status: str = Field(pattern="^(in_review|approved|rejected)$")
    review_note: Optional[str] = Field(default=None, max_length=2000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _table_rows(filters: Optional[Dict[str, Any]] = None, *, limit: int = 500) -> List[Dict[str, Any]]:
    if is_configured():
        try:
            return select_rows("data_lifecycle_requests", filters or None, limit=limit)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Privacy requests could not be read."}) from exc
    return list_rows("data_lifecycle_requests", **(filters or {}))


def _insert_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    if is_configured():
        try:
            return insert_row("data_lifecycle_requests", payload)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Privacy request could not be created."}) from exc
    return insert("data_lifecycle_requests", payload)


def _update_request(request_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if is_configured():
        try:
            return first_update("data_lifecycle_requests", {"lifecycle_request_id": request_id}, patch)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Privacy request could not be updated."}) from exc
    return update_one("data_lifecycle_requests", "lifecycle_request_id", request_id, patch)


def _owned_rows(current_user: CurrentUser) -> List[Dict[str, Any]]:
    rows = _table_rows({"requester_email": current_user.email}, limit=500)
    candidates = (current_user.id, current_user.auth_user_id, current_user.email)
    return [row for row in rows if row_owned_by(row, user_id_candidates=candidates, email=current_user.email)]


def _find_owned_request(request_id: str, current_user: CurrentUser) -> Dict[str, Any]:
    rows = _owned_rows(current_user)
    request = next((row for row in rows if str(row.get("lifecycle_request_id") or row.get("id") or "") == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Privacy request not found."})
    return request


async def _assert_scope_owner(scope: str, project_id: Optional[str], current_user: CurrentUser) -> tuple[str, Optional[str]]:
    try:
        normalized_scope, normalized_project_id = validate_request_scope(scope, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_scope", "message": str(exc)}) from exc
    if normalized_scope == "project" and normalized_project_id:
        await require_project_owner(normalized_project_id, current_user, section="projects")
    return normalized_scope, normalized_project_id


def _active_duplicate(current_user: CurrentUser, *, request_type: str, scope: str, project_id: Optional[str]) -> Optional[Dict[str, Any]]:
    for row in _owned_rows(current_user):
        if is_active_request(row) and same_request_scope(row, request_type=request_type, scope=scope, project_id=project_id):
            return row
    return None


def _create_request(current_user: CurrentUser, *, request_type: str, scope: str, project_id: Optional[str], reason: Optional[str]) -> Dict[str, Any]:
    existing = _active_duplicate(current_user, request_type=request_type, scope=scope, project_id=project_id)
    if existing:
        return {"request": customer_safe_row(existing), "deduplicated": True}
    request_id = make_public_id("privacy")
    payload = request_payload(
        lifecycle_request_id=request_id,
        requester_email=current_user.email,
        requester_user_id=(current_user.auth_user_id if uuid_like(current_user.auth_user_id) else None),
        request_type=request_type,
        scope=scope,
        project_id=project_id,
        reason=reason,
        request_id=current_request_id(),
        policy=policy_from_env(),
    )
    row = _insert_request(payload)
    record_audit_event(
        current_user.payload(),
        f"request.privacy_{request_type}",
        "data_lifecycle_requests",
        request_id,
        {"owner_email": current_user.email, "scope": scope, "project_id": project_id},
    )
    return {"request": customer_safe_row(row), "deduplicated": False}


@router.get("/policy")
async def privacy_policy(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    # Requires a valid session so a future policy may be plan/jurisdiction-aware.
    _ = current_user
    return {
        "policy": policy_from_env().as_dict(),
        "erasure_confirmation": ERASURE_CONFIRMATION,
        "notes": [
            "Erasure requests are reviewed before any destructive action.",
            "Immutable audit records, payments, invoices and encrypted backups may have separate retention obligations.",
            "A request does not automatically delete Supabase Auth identity or private storage objects.",
        ],
    }


@router.get("/requests")
async def list_privacy_requests(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    rows = sorted(_owned_rows(current_user), key=lambda item: str(item.get("requested_at") or item.get("created_at") or ""), reverse=True)
    return {"requests": [customer_safe_row(row) for row in rows], "policy": policy_from_env().as_dict()}


@router.post("/export-requests")
async def create_export_request(payload: DataExportRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    scope, project_id = await _assert_scope_owner(payload.scope, payload.project_id, current_user)
    return _create_request(current_user, request_type="export", scope=scope, project_id=project_id, reason=payload.reason)


@router.post("/erasure-requests")
async def create_erasure_request(payload: DataErasureRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        validate_erasure_confirmation(payload.confirmation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "erasure_confirmation_required", "message": str(exc)}) from exc
    scope, project_id = await _assert_scope_owner(payload.scope, payload.project_id, current_user)
    return _create_request(current_user, request_type="erasure", scope=scope, project_id=project_id, reason=payload.reason)


@router.post("/requests/{request_id}/cancel")
async def cancel_privacy_request(
    request_id: str,
    payload: CancelDataLifecycleRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    request = _find_owned_request(request_id, current_user)
    status = str(request.get("status") or "").lower()
    if status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail={"error": "request_not_cancellable", "message": "Only active privacy requests can be cancelled."})
    updated = _update_request(request_id, {
        "status": "cancelled",
        "cancelled_at": _now(),
        "cancel_reason": str(payload.reason or "").strip()[:1000] or None,
        "updated_at": _now(),
    })
    if not updated:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Privacy request not found."})
    record_audit_event(
        current_user.payload(),
        "cancel.privacy_request",
        "data_lifecycle_requests",
        request_id,
        {"owner_email": current_user.email, "request_type": request.get("request_type"), "scope": request.get("scope")},
    )
    return {"request": customer_safe_row(updated)}
