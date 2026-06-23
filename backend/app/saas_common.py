
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Cookie, HTTPException, UploadFile, File, Request, Header, Response
from pydantic import BaseModel, EmailStr, Field

from .saas_ids import make_public_id, make_guest_token, expiry
from .saas_store import insert, list_rows, find_one, update_one, create_guest_order, log_activity
from .production_store import (
    ProductionStoreError,
    first_update as update_production_row,
    insert_row as insert_production_row,
    is_configured as production_store_configured,
    select_rows as select_production_rows,
    uuid_like,
)
from .version import APP_VERSION
from .saas_credits import credit_summary, require_credit, consume_credit
from .auth_dependencies import CurrentUser
from .access_control import STAFF_ROLES as SUPER_ADMIN_ROLES, SUPER_ADMIN_PERMISSIONS, has_permission as _can_access, normalize_role as _normalize_staff_role, permissions_for
from .services.billing_service import create_checkout_session as create_billing_checkout_session, handle_webhook as handle_billing_webhook
from .services.audit_service import audit_integrity_status, record_audit_event, redact_audit_row
from .supabase_client import is_configured as supabase_is_configured, get_user_from_token, sign_in, sign_up, signed_upload_url, signed_download_url, delete_storage_object, storage_object_path, settings as supabase_settings
from .auth_runtime import verify_supabase_token, get_bearer_token, AuthError, auth_user_payload
from .security_runtime import (
    admin_email_fallback_allowed,
    assert_storage_path_access,
    devbareun_domain_admin_allowed,
    safe_guest_ttl_days,
    runtime_readiness,
    validate_public_token,
    bool_env,
    clear_csrf_cookie,
    production_security_enabled,
    set_csrf_cookie,
)
import os

AUTH_COOKIE = "devbareun_auth"


def _set_auth_cookie(response: Response, token: Optional[str]) -> None:
    if not token:
        return
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        secure=production_security_enabled(),
        samesite="none" if production_security_enabled() else "lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    set_csrf_cookie(response)

PLAN_LIMITS = {
    "single": {"monthly_credits": 1, "label": "Single Project", "kind": "one_time"},
    "plus": {"monthly_credits": 5, "label": "Plus", "kind": "subscription"},
    "pro": {"monthly_credits": 20, "label": "Pro", "kind": "subscription"},
}

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    company_name: Optional[str] = None
    contact_person: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CompanyRequest(BaseModel):
    company_name: str
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    country: Optional[str] = None

class ProjectRequest(BaseModel):
    project_name: str
    location: Optional[str] = None
    contractor: Optional[str] = None
    client: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "AZN"
    project_status: str = "draft"
    analysis_type: str = "all"
    owner_email: Optional[EmailStr] = None

class GuestStartRequest(BaseModel):
    email: EmailStr
    project_name: Optional[str] = None
    result_days: int = Field(default=14, ge=1, le=30)

class CheckoutRequest(BaseModel):
    plan_code: str = Field(pattern="^(single|plus|pro)$")
    project_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    customer_email: Optional[EmailStr] = None

class AnalysisCreateRequest(BaseModel):
    project_id: str
    uploaded_file_ids: List[str] = []
    analysis_type: str = "all"
    package_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    consume_credit_now: bool = True


class StaffCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(owner|support|analyst|finance|operator)$")
    full_name: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|suspended|deactivated)$")


class StaffUpdateRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(owner|support|analyst|finance|operator)$")
    status: Optional[str] = Field(default=None, pattern="^(active|suspended|deactivated)$")
    full_name: Optional[str] = None


class CustomerStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")
    note: Optional[str] = Field(default=None, max_length=1200)


class AdminNoteRequest(BaseModel):
    customer_email: EmailStr
    note: str = Field(min_length=1, max_length=4000)
    project_id: Optional[str] = None


class CreditAdjustmentRequest(BaseModel):
    owner_email: EmailStr
    amount: int = Field(ge=-1000, le=1000)
    reason: str = Field(min_length=3, max_length=1000)
    project_id: Optional[str] = None


class SupportTicketRequest(BaseModel):
    customer_email: EmailStr
    subject: str = Field(min_length=1, max_length=240)
    message: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="open", pattern="^(open|pending|resolved)$")


class SupportTicketUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(open|pending|resolved)$")
    internal_note: Optional[str] = Field(default=None, max_length=4000)


class AuditArchiveRetryRequest(BaseModel):
    reset_attempts: bool = False


def _checkout_current_user(payload: CheckoutRequest) -> CurrentUser:
    email = str(payload.customer_email or "").strip().lower()
    if not email:
        project = find_one("projects", project_id=payload.project_id) if payload.project_id else None
        email = str((project or {}).get("owner_email") or (project or {}).get("customer_email") or "").strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Customer email is required for checkout.")
    return CurrentUser(id="", auth_user_id="", email=email, plan=payload.plan_code)

class SupabaseAuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    company_name: Optional[str] = None
    contact_person: Optional[str] = None

class StorageSignRequest(BaseModel):
    project_id: str
    file_name: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None

class StorageDownloadRequest(BaseModel):
    storage_path: str
    expires_in: int = Field(default=3600, ge=60, le=86400)

class StorageUploadCompleteRequest(BaseModel):
    file_id: str
    project_id: str
    storage_path: str
    uploaded: bool = True
    checksum: Optional[str] = None

def _session_token(authorization: Optional[str], auth_cookie: Optional[str] = None) -> str:
    token = get_bearer_token(authorization) or auth_cookie
    if not token:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "A valid session is required."})
    return token

def _supabase_user_from_session(authorization: Optional[str], auth_cookie: Optional[str] = None) -> Dict[str, Any]:
    token = _session_token(authorization, auth_cookie)
    try:
        return get_user_from_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or expired session."}) from exc

def _upsert_local_user_from_supabase(auth_user: Dict[str, Any]) -> Dict[str, Any]:
    email = auth_user.get("email") or (auth_user.get("user") or {}).get("email")
    supabase_user_id = auth_user.get("id") or (auth_user.get("user") or {}).get("id")
    if not email:
        raise HTTPException(status_code=400, detail="Supabase user payload does not include email.")
    existing = find_one("users", email=email)
    if existing:
        return update_one("users", "user_id", existing["user_id"], {"supabase_user_id": supabase_user_id, "status": "active", "auth_provider": "supabase"}) or existing
    return insert("users", {
        "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
        "email": email,
        "supabase_user_id": supabase_user_id,
        "auth_provider": "supabase",
        "status": "active",
        "role": "customer",
    })


def _optional_saas_user(authorization: Optional[str], auth_cookie: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not (authorization or auth_cookie):
        return None
    auth_user = _supabase_user_from_session(authorization, auth_cookie)
    return _upsert_local_user_from_supabase(auth_user)


def _required_saas_user(authorization: Optional[str], auth_cookie: Optional[str] = None) -> Dict[str, Any]:
    user = _optional_saas_user(authorization, auth_cookie)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "A valid session is required."})
    return user


def _assert_project_owner(project: Dict[str, Any], user: Optional[Dict[str, Any]]) -> None:
    if not user:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
    owner_email = project.get("owner_email")
    if not owner_email:
        raise HTTPException(status_code=403, detail="Project ownership is not initialized.")
    if owner_email and owner_email != user.get("email"):
        raise HTTPException(status_code=403, detail="You can access only your own project.")


def _assert_file_owner(file_row: Dict[str, Any], user: Optional[Dict[str, Any]]) -> None:
    if not user:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
    owner_email = file_row.get("owner_email")
    if not owner_email:
        raise HTTPException(status_code=403, detail="File ownership is not initialized.")
    if owner_email and owner_email != user.get("email"):
        raise HTTPException(status_code=403, detail="You can access only your own file.")

def _admin_emails() -> set[str]:
    raw = os.getenv("DEVBAREUN_ADMIN_EMAILS", "").strip()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _is_admin_email(email: str | None) -> bool:
    value = (email or "").strip().lower()
    if not value:
        return False
    if value in _admin_emails():
        return True
    if admin_email_fallback_allowed() and devbareun_domain_admin_allowed() and value.endswith("@devbareun.com"):
        return True
    return False


async def require_admin_user(authorization: Optional[str]) -> Dict[str, Any]:
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Admin bearer token is required.")
    try:
        user = await verify_supabase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or expired session."}) from exc
    if not (bool(user.is_admin) or _is_admin_email(user.email)):
        raise HTTPException(status_code=403, detail="Admin role is required for this resource.")
    return auth_user_payload(user)


def _search_rows(rows: List[Dict[str, Any]], q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None) -> List[Dict[str, Any]]:
    result = list(rows)
    if status:
        result = [
            r for r in result
            if str(
                r.get("status")
                or r.get("project_status")
                or r.get("payment_status")
                or r.get("upload_status")
                or r.get("parser_status")
                or r.get("current_status")
                or ""
            ).lower() == status.lower()
        ]
    if project_id:
        result = [r for r in result if str(r.get("project_id") or "") == project_id]
    if owner_email:
        email = owner_email.lower()
        result = [r for r in result if email in str(r.get("owner_email") or r.get("email") or r.get("customer_email") or "").lower()]
    if q:
        needle = q.lower()
        result = [r for r in result if needle in str(r).lower()]
    result.sort(key=lambda r: str(r.get("created_at") or r.get("created_at_ts") or r.get("updated_at") or ""), reverse=True)
    return result


def _limited(rows: List[Dict[str, Any]], limit: int = 200) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 200), 1000))
    return rows[:limit]


def _failed_upload_rows() -> List[Dict[str, Any]]:
    failed_statuses = {"failed", "error", "rejected", "upload_failed", "parse_failed", "virus_rejected", "deleted"}
    rows = []
    for row in _production_rows("uploaded_files"):
        status = str(row.get("status") or row.get("upload_status") or "").lower()
        parser_status = str(row.get("parser_status") or "").lower()
        if status in failed_statuses or parser_status in failed_statuses or row.get("failure_reason") or row.get("error_message"):
            rows.append(row)
    return rows


# Canonical panel policy is defined in ``access_control``. The aliases above
# remain in this module because existing admin routers import them via
# ``from .saas_common import *``.


PRODUCTION_TABLE_ALIASES = {
    "users": "users_profile",
}


def _production_table(table: str) -> str:
    return PRODUCTION_TABLE_ALIASES.get(table, table) if production_store_configured() else table


def _production_payload(table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if table != "users" or not production_store_configured():
        return payload
    allowed = {
        "auth_user_id", "email", "full_name", "role", "status", "company_id", "plan",
        "user_id", "auth_provider",
    }
    return {key: value for key, value in payload.items() if key in allowed and value is not None}


def _production_rows(table: str, *, limit: int = 1000, **filters: Any) -> List[Dict[str, Any]]:
    if not production_store_configured():
        return list_rows(table, **filters)
    clean_filters = {key: value for key, value in filters.items() if value is not None}
    try:
        return select_production_rows(_production_table(table), clean_filters or None, limit=limit)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": f"{table} could not be read."}) from exc


def _production_insert(table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not production_store_configured():
        return insert(table, payload)
    try:
        return insert_production_row(_production_table(table), _production_payload(table, payload))
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": f"{table} could not be written."}) from exc


def _production_update(table: str, public_key: str, public_value: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    if not production_store_configured():
        row = update_one(table, public_key, public_value, patch)
        if not row:
            raise HTTPException(status_code=404, detail=f"{table} record was not found.")
        return row
    try:
        row = update_production_row(_production_table(table), {public_key: public_value}, _production_payload(table, patch))
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": f"{table} could not be updated."}) from exc
    if not row:
        raise HTTPException(status_code=404, detail=f"{table} record was not found.")
    return row


def _safe_upload_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hidden = {"storage_path", "signed_url", "download_url", "public_url"}
    return [{key: value for key, value in row.items() if key not in hidden} for row in rows]


def _admin_profile_for_email(email: str, auth_payload: Dict[str, Any]) -> Dict[str, Any]:
    local_user = find_one("users", email=email)
    role = _normalize_staff_role((local_user or {}).get("role"), bool(auth_payload.get("is_admin")))
    status = str((local_user or {}).get("status") or "active").lower()
    if production_store_configured():
        try:
            profiles = select_production_rows("users_profile", {"email": email}, limit=1)
            if profiles:
                profile = profiles[0]
                role = _normalize_staff_role(profile.get("role"), bool(auth_payload.get("is_admin")))
                status = str(profile.get("status") or status).lower()
                local_user = {**(local_user or {}), **profile}
        except ProductionStoreError:
            pass
    if _is_admin_email(email) or bool(auth_payload.get("is_admin")):
        role = "owner" if role == "customer" else role
    return {
        **auth_payload,
        "email": email,
        "role": role,
        "status": status,
        "permissions": permissions_for(role),
        "profile": local_user or {},
    }


async def require_super_admin_user(
    authorization: Optional[str],
    section: str = "overview",
    auth_cookie: Optional[str] = None,
) -> Dict[str, Any]:
    token = get_bearer_token(authorization) or auth_cookie
    if not token:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Super admin bearer token is required."})
    try:
        user = await verify_supabase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or expired session."}) from exc
    payload = _admin_profile_for_email(user.email, auth_user_payload(user))
    if payload["status"] != "active":
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Staff account is not active."})
    if not _can_access(payload["role"], section):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": f"{payload['role']} cannot access {section}."})
    return payload


def _audit(admin: Dict[str, Any], action: str, entity_type: str, entity_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    # Durable audit writes are append-only in production through the
    # ``append_audit_event`` RPC. Read-only pages remain resilient if the
    # audit store is temporarily unavailable; mutation endpoints still keep
    # their primary state-change behavior explicit in their own contracts.
    record_audit_event(admin, action, entity_type, entity_id, metadata)


def _admin_counts() -> Dict[str, int]:
    analysis_rows = _production_rows("analysis_results")
    job_rows = _production_rows("analysis_jobs")
    credit_rows = _production_rows("analysis_credits")
    failed_analyses = [
        row for row in [*analysis_rows, *job_rows]
        if str(row.get("status") or "").lower() in {"failed", "error", "cancelled", "rejected"}
        or row.get("error_message")
    ]
    pending_analyses = [
        row for row in [*analysis_rows, *job_rows]
        if str(row.get("status") or "").lower() in {"queued", "pending", "processing", "running", "created"}
    ]
    return {
        "users": len(_production_rows("users")),
        "companies": len(_production_rows("companies")),
        "projects": len(_production_rows("projects")),
        "uploads": len(_production_rows("uploaded_files")),
        "payments": len(_production_rows("payments")),
        "reports": len(_production_rows("reports")),
        "failed_uploads": len(_failed_upload_rows()),
        "credit_usage": len(_production_rows("subscription_usage")),
        "activity_logs": len(_production_rows("activity_logs")),
        "audit_logs": len(_production_rows("audit_logs")),
        "support_tickets": len(_production_rows("support_tickets")),
        "analysis_results": len(analysis_rows),
        "pending_analyses": len(pending_analyses),
        "failed_analyses": len(failed_analyses),
        "used_credits": sum(int(row.get("used_credits") or row.get("amount") or 0) for row in credit_rows),
        "checkout_sessions": len(_production_rows("checkout_sessions")),
        "subscriptions": len(_production_rows("subscriptions")),
        "guest_orders": len(_production_rows("guest_orders")),
    }




# Export underscored helper functions to the split route modules.
__all__ = [name for name in globals() if not name.startswith("__")]
