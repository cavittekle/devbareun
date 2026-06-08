
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
from .services.billing_service import create_checkout_session as create_billing_checkout_session, handle_webhook as handle_billing_webhook
from .supabase_client import is_configured as supabase_is_configured, get_user_from_token, sign_in, sign_up, signed_upload_url, signed_download_url, delete_storage_object, storage_object_path, settings as supabase_settings
from .auth_runtime import verify_supabase_token, get_bearer_token, AuthError, auth_user_payload
from .security_runtime import (
    admin_email_fallback_allowed,
    assert_storage_path_access,
    devbareun_domain_admin_allowed,
    safe_guest_ttl_days,
    validate_public_token,
    bool_env,
    production_security_enabled,
)
import os

router = APIRouter(prefix="/api", tags=["DevBareun SaaS Foundation"])
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

def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Use Authorization: Bearer <supabase_access_token>.")
    return parts[1]

def _supabase_user_from_header(authorization: Optional[str]) -> Dict[str, Any]:
    token = _bearer_token(authorization)
    try:
        return get_user_from_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Supabase token: {exc}") from exc

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
        "role": "owner",
    })


def _optional_saas_user(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    auth_user = _supabase_user_from_header(authorization)
    return _upsert_local_user_from_supabase(auth_user)


def _required_saas_user(authorization: Optional[str]) -> Dict[str, Any]:
    user = _optional_saas_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
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


SUPER_ADMIN_ROLES = {"owner", "support", "analyst", "finance", "operator"}
SUPER_ADMIN_PERMISSIONS = {
    "owner": {
        "overview", "customers", "projects", "uploads", "reports", "payments", "credits",
        "support", "activity", "audit", "staff", "notes"
    },
    "support": {"overview", "customers", "support", "activity", "notes"},
    "analyst": {"overview", "projects", "uploads", "reports", "activity"},
    "finance": {"overview", "payments", "credits", "activity"},
    "operator": {"overview", "projects", "reports", "activity"},
}


def _normalize_staff_role(role: Optional[str], is_admin: bool = False) -> str:
    value = str(role or "").strip().lower()
    if value == "admin":
        return "owner"
    if value in SUPER_ADMIN_ROLES:
        return value
    return "owner" if is_admin else "customer"


def _can_access(role: str, section: str) -> bool:
    return section in SUPER_ADMIN_PERMISSIONS.get(_normalize_staff_role(role), set())


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
        "permissions": sorted(SUPER_ADMIN_PERMISSIONS.get(role, set())),
        "profile": local_user or {},
    }


async def require_super_admin_user(authorization: Optional[str], section: str = "overview") -> Dict[str, Any]:
    token = get_bearer_token(authorization)
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
    try:
        _production_insert("audit_logs", {
            "audit_id": make_public_id("audit"),
            "actor_email": admin.get("email"),
            "actor_role": admin.get("role"),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata or {},
        })
    except Exception:
        # Audit logging must not expose internals or break read-only admin pages.
        pass


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


@router.get("/saas/health")
def saas_health() -> Dict[str, Any]:
    return {"status": "ok", "module": "saas-foundation", "version": APP_VERSION, "plans": PLAN_LIMITS, "supabase_configured": supabase_is_configured(), "storage_bucket": supabase_settings().storage_bucket}

@router.post("/auth/supabase/register")
def supabase_register(payload: SupabaseAuthRequest) -> Dict[str, Any]:
    if not supabase_is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    try:
        auth_payload = sign_up(str(payload.email), payload.password, {"company_name": payload.company_name, "contact_person": payload.contact_person})
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "signup_failed", "message": "Registration could not be completed. Check the email and try again."}) from exc
    user = find_one("users", email=str(payload.email))
    if not user:
        user = insert("users", {
            "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
            "email": str(payload.email),
            "auth_provider": "supabase",
            "status": "pending_email_confirmation",
            "role": "owner",
        })
    company = None
    if payload.company_name and not find_one("companies", email=str(payload.email)):
        company = insert("companies", {
            "company_id": make_public_id("company"),
            "company_name": payload.company_name,
            "contact_person": payload.contact_person,
            "email": str(payload.email),
            "subscription_plan": "free",
        })
    log_activity(str(payload.email), "auth.supabase_register", {"user_id": user.get("user_id")})
    return {"status": "supabase_signup_started", "auth": auth_payload, "user": user, "company": company}

@router.post("/auth/supabase/login")
def supabase_login(payload: SupabaseAuthRequest, response: Response) -> Dict[str, Any]:
    if not supabase_is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    try:
        auth_payload = sign_in(str(payload.email), payload.password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail={"error": "login_failed", "message": "Email or password is incorrect."}) from exc
    _set_auth_cookie(response, (auth_payload.get("auth") or auth_payload).get("access_token"))
    user_payload = auth_payload.get("user") or {}
    local_user = _upsert_local_user_from_supabase(user_payload or {"email": str(payload.email)})
    return {"status": "authenticated", "auth": auth_payload, "user": local_user}

@router.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_header(authorization or (f"Bearer {auth_cookie}" if auth_cookie else None))
    local_user = _upsert_local_user_from_supabase(auth_user)
    return {"auth_user": auth_user, "user": local_user}

@router.post("/storage/create-upload-url")
def create_storage_upload_url(payload: StorageSignRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_header(authorization)
    user = _upsert_local_user_from_supabase(auth_user)
    project = find_one("projects", project_id=payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    owner_email = project.get("owner_email") or user.get("email")
    if project.get("owner_email") is None:
        project = update_one("projects", "project_id", payload.project_id, {"owner_email": owner_email}) or project
    if owner_email and owner_email != user.get("email"):
        raise HTTPException(status_code=403, detail="You can only upload files to your own project.")
    file_id = make_public_id("file")
    path = storage_object_path(payload.project_id, file_id, payload.file_name)
    try:
        signed = signed_upload_url(path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not create Supabase signed upload URL: {exc}") from exc
    file_row = insert("uploaded_files", {
        "file_id": file_id,
        "project_id": payload.project_id,
        "owner_email": user.get("email"),
        "original_name": payload.file_name,
        "content_type": payload.content_type,
        "size_bytes": payload.size_bytes,
        "storage_provider": "supabase_storage",
        "storage_bucket": supabase_settings().storage_bucket,
        "storage_path": path,
        "status": "awaiting_upload",
        "upload_progress": 0,
    })
    log_activity(user.get("email"), "file.signed_upload_url_created", {"project_id": payload.project_id, "file_id": file_id})
    return {"file": file_row, "upload": signed}

@router.post("/storage/mark-uploaded")
def mark_storage_uploaded(payload: StorageUploadCompleteRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_header(authorization)
    user = _upsert_local_user_from_supabase(auth_user)
    file_row = find_one("uploaded_files", file_id=payload.file_id)
    if not file_row:
        raise HTTPException(status_code=404, detail="File record not found.")
    _assert_file_owner(file_row, user)
    if file_row.get("project_id") != payload.project_id or file_row.get("storage_path") != payload.storage_path:
        raise HTTPException(status_code=400, detail="File/project/storage path mismatch.")
    updated = update_one("uploaded_files", "file_id", payload.file_id, {
        "status": "uploaded",
        "upload_progress": 100,
        "uploaded_at": datetime.utcnow().isoformat(),
        "checksum": payload.checksum,
    })
    log_activity(user.get("email"), "file.upload_completed", {"project_id": payload.project_id, "file_id": payload.file_id})
    return {"file": updated}

@router.post("/storage/create-download-url")
def create_storage_download_url(payload: StorageDownloadRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_header(authorization)
    user = _upsert_local_user_from_supabase(auth_user)
    file_row = find_one("uploaded_files", storage_path=payload.storage_path)
    assert_storage_path_access(file_row, user.get("email"), payload.storage_path)
    try:
        signed = signed_download_url(payload.storage_path, payload.expires_in)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not create Supabase signed download URL: {exc}") from exc
    return {"download": signed, "file": file_row}

# Auth skeleton. Production should use Supabase Auth or Clerk; this endpoint creates local SaaS records only.
@router.post("/auth/register")
def register(payload: RegisterRequest) -> Dict[str, Any]:
    existing = find_one("users", email=str(payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="User already exists. Use Supabase Auth in production.")
    user = insert("users", {
        "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
        "email": str(payload.email),
        "auth_provider": "supabase_auth_expected",
        "status": "pending_auth_provider",
        "role": "owner",
    })
    company = None
    if payload.company_name:
        company = insert("companies", {
            "company_id": make_public_id("company"),
            "company_name": payload.company_name,
            "contact_person": payload.contact_person,
            "email": str(payload.email),
            "subscription_plan": "free",
        })
    log_activity(str(payload.email), "auth.register_skeleton", {"user_id": user["user_id"]})
    return {"user": user, "company": company, "note": "Production auth should be completed through Supabase Auth or Clerk."}

@router.post("/auth/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    user = find_one("users", email=str(payload.email))
    if not user:
        raise HTTPException(status_code=404, detail="User record not found. Connect Supabase Auth for production login.")
    return {"status": "auth_provider_required", "user": user, "note": "Use Supabase Auth token exchange in production."}

@router.post("/auth/logout")
def logout() -> Dict[str, str]:
    return {"status": "ok", "message": "Client should clear auth session through the auth provider."}

@router.get("/users/profile")
def profile(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    current = _required_saas_user(authorization)
    user = find_one("users", email=current.get("email"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user": user}

@router.post("/companies/create")
def create_company(payload: CompanyRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    current = _required_saas_user(authorization)
    row = payload.model_dump()
    row["owner_email"] = current.get("email")
    row["email"] = row.get("email") or current.get("email")
    company = insert("companies", {**row, "company_id": make_public_id("company"), "subscription_plan": "free"})
    return {"company": company}

@router.post("/companies/update")
def update_company(company_id: str, payload: CompanyRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    current = _required_saas_user(authorization)
    existing = find_one("companies", company_id=company_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found.")
    if existing.get("owner_email") and existing.get("owner_email") != current.get("email"):
        raise HTTPException(status_code=403, detail="You can update only your own company.")
    company = update_one("companies", "company_id", company_id, payload.model_dump(exclude_unset=True))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return {"company": company}

@router.post("/projects/create")
def create_saas_project(payload: ProjectRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    row = payload.model_dump()
    if production_store_configured():
        project_payload = {
            "user_id": user.get("supabase_user_id") if uuid_like(str(user.get("supabase_user_id") or "")) else None,
            "project_name": row.get("project_name"),
            "location": row.get("location"),
            "client_name": row.get("client"),
            "contractor_name": row.get("contractor"),
            "contract_value": row.get("contract_value"),
            "currency": row.get("currency") or "AZN",
            "start_date": row.get("start_date") or None,
            "planned_finish_date": row.get("end_date") or None,
            "current_status": row.get("project_status") or "draft",
            "owner_email": user.get("email"),
        }
        project_payload = {key: value for key, value in project_payload.items() if value not in (None, "")}
        try:
            project = insert_production_row("projects", project_payload)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project could not be created."}) from exc
        project.setdefault("project_id", str(project.get("id") or ""))
        return {"project": project}
    row["owner_email"] = user.get("email")
    row.setdefault("status", row.get("project_status") or "draft")
    project = insert("projects", {**row, "project_id": make_public_id("project")})
    log_activity(project.get("owner_email"), "project.create", {"project_id": project["project_id"]})
    return {"project": project}

@router.get("/projects/list")
def list_projects(owner_email: Optional[str] = None, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    effective_owner = user.get("email")
    return {"projects": list_rows("projects", owner_email=effective_owner)}

@router.get("/projects/{project_id}")
def get_saas_project(project_id: str, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    project = find_one("projects", project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    files = [row for row in list_rows("uploaded_files", project_id=project_id) if row.get("status") != "deleted"]
    analyses = list_rows("analysis_results", project_id=project_id)
    return {"project": project, "uploaded_files": files, "analysis_results": analyses}

@router.post("/guest/start")
def start_guest_project(payload: GuestStartRequest) -> Dict[str, Any]:
    result = create_guest_order(str(payload.email), payload.project_name, safe_guest_ttl_days(payload.result_days))
    log_activity(str(payload.email), "guest.start", {"project_id": result["project"]["project_id"]})
    return result

@router.post("/files/upload")
async def upload_saas_files(project_id: str, files: List[UploadFile] = File(...), authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    project = find_one("projects", project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Create project before upload.")
    _assert_project_owner(project, user)
    uploaded = []
    for f in files:
        # This skeleton records metadata. Existing /api/projects/{id}/upload remains the file parser upload path.
        file_id = make_public_id("file")
        row = insert("uploaded_files", {
            "file_id": file_id,
            "project_id": project_id,
            "original_name": f.filename,
            "content_type": f.content_type,
            "size_bytes": getattr(f, "size", None),
            "owner_email": user.get("email"),
            "storage_provider": "supabase_storage_expected",
            "storage_path": f"projects/{project_id}/{file_id}/{f.filename}",
            "status": "metadata_recorded",
        })
        uploaded.append(row)
    return {"project_id": project_id, "uploaded_files": uploaded}

@router.delete("/files/delete")
def delete_file(file_id: str, authorization: Optional[str] = Header(default=None), delete_object: bool = True) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    current = find_one("uploaded_files", file_id=file_id)
    if not current:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_file_owner(current, user)
    storage_delete_status = "not_requested"
    if delete_object and current.get("storage_path") and current.get("storage_provider") == "supabase_storage":
        try:
            delete_storage_object(current["storage_path"])
            storage_delete_status = "deleted"
        except Exception as exc:
            storage_delete_status = f"storage_delete_failed: {exc}"
    file_row = update_one("uploaded_files", "file_id", file_id, {"status": "deleted", "deleted_at": datetime.utcnow().isoformat(), "storage_delete_status": storage_delete_status})
    log_activity(user.get("email") if user else current.get("owner_email"), "file.delete", {"file_id": file_id, "storage_delete_status": storage_delete_status})
    return {"status": "deleted", "file": file_row, "storage_delete_status": storage_delete_status}

@router.get("/files/list")
def list_files(project_id: str, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    project = find_one("projects", project_id=project_id)
    if project:
        _assert_project_owner(project, user)
    return {"uploaded_files": [row for row in list_rows("uploaded_files", project_id=project_id) if row.get("status") != "deleted"]}

@router.post("/analysis/create")
def create_analysis_record(payload: AnalysisCreateRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    project = find_one("projects", project_id=payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    owner_email = user.get("email")
    if payload.uploaded_file_ids:
        for file_id in payload.uploaded_file_ids:
            file_row = find_one("uploaded_files", file_id=file_id)
            if not file_row or file_row.get("project_id") != payload.project_id or file_row.get("status") not in {"uploaded", "metadata_recorded", "local_record"}:
                raise HTTPException(status_code=400, detail=f"File {file_id} is not uploaded or does not belong to this project.")
            _assert_file_owner(file_row, user)
    credit_check = require_credit(owner_email=owner_email, project_id=payload.project_id)
    if not credit_check.get("allowed"):
        raise HTTPException(status_code=402, detail={
            "message": "No analysis credits available. Complete payment, upgrade plan, or buy an extra project review.",
            "credits": credit_check,
        })
    analysis = insert("analysis_results", {
        "analysis_id": make_public_id("analysis"),
        "project_id": payload.project_id,
        "uploaded_file_ids": payload.uploaded_file_ids,
        "analysis_type": payload.analysis_type,
        "package_name": payload.package_name or payload.analysis_type,
        "owner_email": owner_email,
        "status": "queued",
        "result_json": {},
    })
    credit_usage = None
    if payload.consume_credit_now:
        credit_usage = consume_credit(owner_email=owner_email, project_id=payload.project_id, analysis_id=analysis["analysis_id"])
    log_activity(owner_email, "analysis.create", {"analysis_id": analysis["analysis_id"], "project_id": payload.project_id})
    return {"analysis": analysis, "credit_usage": credit_usage, "note": "Call existing project analyze endpoint to run current parser/dashboard engine."}

@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    row = find_one("analysis_results", analysis_id=analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if row.get("owner_email") != user.get("email"):
        raise HTTPException(status_code=403, detail="You can access only your own analysis.")
    return {"analysis": row}

@router.get("/guest-result/{token}")
def guest_result(token: str) -> Dict[str, Any]:
    token = validate_public_token(token, "guest result link")
    order = find_one("guest_orders", result_token=token)
    if not order:
        raise HTTPException(status_code=404, detail="Guest result link not found.")
    if order.get("result_expires_at") and order["result_expires_at"] < datetime.utcnow().isoformat():
        raise HTTPException(status_code=410, detail="Guest result link has expired.")
    project = find_one("projects", guest_order_id=order.get("guest_order_id"))
    analyses = list_rows("analysis_results", project_id=project.get("project_id") if project else None)
    return {"guest_order": order, "project": project, "analysis_results": analyses}

@router.post("/payments/create-one-time-checkout")
def create_one_time_checkout(payload: CheckoutRequest) -> Dict[str, Any]:
    if payload.plan_code != "single":
        raise HTTPException(status_code=400, detail="Use create-subscription-checkout for Plus or Pro.")
    try:
        return create_billing_checkout_session(_checkout_current_user(payload), payload.plan_code, payload.project_id, payload.success_url, payload.cancel_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "checkout_failed", "message": "Checkout could not be created. Please try again."}) from exc

@router.post("/payments/create-subscription-checkout")
def create_subscription_checkout(payload: CheckoutRequest) -> Dict[str, Any]:
    if payload.plan_code not in {"plus", "pro"}:
        raise HTTPException(status_code=400, detail="Subscription checkout supports Plus and Pro only.")
    try:
        return create_billing_checkout_session(_checkout_current_user(payload), payload.plan_code, payload.project_id, payload.success_url, payload.cancel_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "checkout_failed", "message": "Checkout could not be created. Please try again."}) from exc

@router.post("/payments/activate-pilot-checkout")
def activate_pilot_checkout(checkout_id: str, customer_email: Optional[EmailStr] = None) -> Dict[str, Any]:
    """Pilot helper for non-production checkout testing. Disable before production launch."""
    if production_security_enabled() or not bool_env("DEVBAREUN_ENABLE_PILOT_CHECKOUT", False):
        raise HTTPException(status_code=403, detail="Pilot checkout activation is disabled.")
    session = find_one("checkout_sessions", checkout_id=checkout_id)
    if not session:
        raise HTTPException(status_code=404, detail="Pilot checkout session was not found.")
    owner_email = str(customer_email or session.get("customer_email") or f"guest-{checkout_id.lower()}@devbareun.local")
    payment = insert("payments", {
        "payment_id": make_public_id("payment"),
        "checkout_id": checkout_id,
        "owner_email": owner_email,
        "project_id": session.get("project_id"),
        "plan_code": session.get("plan_code") or "single",
        "status": "paid",
        "paid_at": datetime.utcnow().isoformat(),
    })
    update_one("checkout_sessions", "checkout_id", checkout_id, {"status": "paid", "paid_at": datetime.utcnow().isoformat()})
    return {"status": "activated", "payment": payment}

@router.post("/payments/webhook")
async def payment_webhook(request: Request) -> Dict[str, Any]:
    body = await request.body()
    try:
        return handle_billing_webhook(body, request.headers.get("x-signature"), provider_hint="lemonsqueezy")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Payment webhook rejected: {exc}") from exc

@router.get("/subscriptions/status")
def subscription_status(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    return {"subscriptions": list_rows("subscriptions", owner_email=user.get("email"))}

@router.get("/credits/status")
def credits_status(project_id: Optional[str] = None, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = _required_saas_user(authorization)
    return {"credit_summary": credit_summary(owner_email=user.get("email"), project_id=project_id)}

@router.get("/admin/me")
async def admin_me(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "overview")
    return {"admin": admin, "counts": _admin_counts()}


@router.get("/admin/overview")
async def admin_overview(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "overview")
    counts = _admin_counts()
    payments = _search_rows(_production_rows("payments"), None)[:8]
    logs = _search_rows(_production_rows("activity_logs"), None)[:12]
    failed = _failed_upload_rows()[:8]
    credits = credit_summary()
    _audit(admin, "view.overview", "super_admin")
    return {
        "admin": admin,
        "counts": counts,
        "payments_recent": payments,
        "activity_recent": logs,
        "failed_uploads_recent": failed,
        "credits": credits,
    }


@router.get("/admin/users")
async def admin_users(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers")
    rows = _search_rows(_production_rows("users"), q=q, status=status)
    _audit(admin, "view.customers", "users")
    return {"users": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/companies")
async def admin_companies(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers")
    rows = _search_rows(_production_rows("companies"), q=q, status=status)
    _audit(admin, "view.companies", "companies")
    return {"companies": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/projects")
async def admin_projects(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "projects")
    rows = _search_rows(_production_rows("projects"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.projects", "projects")
    return {"projects": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/payments")
async def admin_payments(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "payments")
    payments = _search_rows(_production_rows("payments"), q=q, status=status, owner_email=owner_email)
    sessions = _search_rows(_production_rows("checkout_sessions"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.payments", "payments")
    return {"payments": _limited(payments, limit), "checkout_sessions": _limited(sessions, limit), "total": len(payments) + len(sessions)}


@router.get("/admin/reports")
async def admin_reports(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "reports")
    rows = _search_rows(_production_rows("reports"), q=q, status=status, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.reports", "reports")
    return {"reports": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/failed-uploads")
async def admin_failed_uploads(q: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "uploads")
    rows = _search_rows(_failed_upload_rows(), q=q, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.failed_uploads", "uploaded_files")
    return {"failed_uploads": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/credit-usage")
async def admin_credit_usage(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "credits")
    credits = _search_rows(_production_rows("analysis_credits"), q=q, owner_email=owner_email)
    usage = _search_rows(_production_rows("subscription_usage"), q=q, owner_email=owner_email)
    totals = {
        "credits_total": sum(int(r.get("total_credits") or 0) for r in credits),
        "credits_used": sum(int(r.get("used_credits") or 0) for r in credits),
        "credits_remaining": sum(int(r.get("remaining_credits") or 0) for r in credits),
        "usage_events": len(usage),
    }
    _audit(admin, "view.credits", "analysis_credits")
    return {"analysis_credits": _limited(credits, limit), "subscription_usage": _limited(usage, limit), "totals": totals, "total": len(credits) + len(usage)}


@router.get("/admin/activity-logs")
async def admin_activity_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "activity")
    rows = _search_rows(_production_rows("activity_logs"), q=q, owner_email=owner_email)
    _audit(admin, "view.activity_logs", "activity_logs")
    return {"activity_logs": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/logs")
async def admin_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_activity_logs(q=q, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/admin/uploads")
async def admin_uploads(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "uploads")
    rows = _search_rows(_safe_upload_rows(_production_rows("uploaded_files")), q=q, status=status, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.uploads", "uploaded_files")
    return {"uploads": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/support-tickets")
async def admin_support_tickets(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support")
    rows = _search_rows(_production_rows("support_tickets"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.support_tickets", "support_tickets")
    return {"support_tickets": _limited(rows, limit), "total": len(rows)}


@router.post("/admin/support-tickets")
async def admin_create_support_ticket(payload: SupportTicketRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support")
    row = _production_insert("support_tickets", {
        "ticket_id": make_public_id("ticket"),
        "customer_email": str(payload.customer_email).lower(),
        "owner_email": str(payload.customer_email).lower(),
        "subject": payload.subject,
        "message": payload.message,
        "status": payload.status,
        "created_by_email": admin.get("email"),
    })
    _audit(admin, "create.support_ticket", "support_tickets", row.get("ticket_id"), {"customer_email": str(payload.customer_email)})
    return {"support_ticket": row}


@router.patch("/admin/support-tickets/{ticket_id}")
async def admin_update_support_ticket(ticket_id: str, payload: SupportTicketUpdateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support")
    patch = payload.model_dump(exclude_unset=True)
    if payload.internal_note:
        patch["last_internal_note"] = payload.internal_note
        patch["last_internal_note_by"] = admin.get("email")
    row = _production_update("support_tickets", "ticket_id", ticket_id, patch)
    _audit(admin, "update.support_ticket", "support_tickets", ticket_id, patch)
    return {"support_ticket": row}


@router.get("/admin/audit-logs")
async def admin_audit_logs(q: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "audit")
    rows = _search_rows(_production_rows("audit_logs"), q=q)
    _audit(admin, "view.audit_logs", "audit_logs")
    return {"audit_logs": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/staff")
async def admin_staff(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff")
    rows = [
        row for row in _search_rows(_production_rows("users"), q=q, status=status)
        if _normalize_staff_role(row.get("role")) in SUPER_ADMIN_ROLES
    ]
    _audit(admin, "view.staff", "users")
    return {"staff": _limited(rows, limit), "total": len(rows), "roles": sorted(SUPER_ADMIN_ROLES)}


@router.post("/admin/staff")
async def admin_create_staff(payload: StaffCreateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff")
    if payload.role == "owner" and admin.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can create owner users.")
    existing_rows = _production_rows("users", email=str(payload.email).lower(), limit=1)
    existing = existing_rows[0] if existing_rows else None
    if existing and existing.get("email") == admin.get("email"):
        raise HTTPException(status_code=403, detail="You cannot change your own permissions.")
    row_payload = {
        "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
        "email": str(payload.email).lower(),
        "full_name": payload.full_name,
        "role": payload.role,
        "status": payload.status,
        "auth_provider": "supabase",
    }
    row = _production_update("users", "email", str(payload.email).lower(), row_payload) if existing else _production_insert("users", row_payload)
    _audit(admin, "upsert.staff", "users", row.get("user_id") or row.get("id"), {"staff_email": str(payload.email), "role": payload.role})
    return {"staff_user": row}


@router.patch("/admin/staff/{email}")
async def admin_update_staff(email: str, payload: StaffUpdateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff")
    email = email.strip().lower()
    if email == str(admin.get("email") or "").lower():
        raise HTTPException(status_code=403, detail="Staff cannot change their own permissions.")
    if payload.role == "owner" and admin.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can assign owner role.")
    patch = payload.model_dump(exclude_unset=True)
    row = _production_update("users", "email", email, patch)
    _audit(admin, "update.staff", "users", row.get("user_id") or row.get("id"), {"staff_email": email, **patch})
    return {"staff_user": row}


@router.patch("/admin/customers/{email}/status")
async def admin_update_customer_status(email: str, payload: CustomerStatusRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers")
    email = email.strip().lower()
    row = _production_update("users", "email", email, {"status": payload.status})
    note = None
    if payload.note:
        note = _production_insert("admin_notes", {
            "note_id": make_public_id("note"),
            "customer_email": email,
            "owner_email": email,
            "note": payload.note,
            "created_by_email": admin.get("email"),
        })
    _audit(admin, f"customer.{payload.status}", "users", row.get("user_id") or row.get("id"), {"customer_email": email})
    return {"customer": row, "admin_note": note}


@router.get("/admin/notes")
async def admin_notes(customer_email: Optional[str] = None, project_id: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "notes")
    rows = _production_rows("admin_notes", owner_email=customer_email, project_id=project_id)
    _audit(admin, "view.admin_notes", "admin_notes")
    return {"admin_notes": _limited(rows, limit), "total": len(rows)}


@router.post("/admin/notes")
async def admin_create_note(payload: AdminNoteRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "notes")
    row = _production_insert("admin_notes", {
        "note_id": make_public_id("note"),
        "customer_email": str(payload.customer_email).lower(),
        "owner_email": str(payload.customer_email).lower(),
        "project_id": payload.project_id,
        "note": payload.note,
        "created_by_email": admin.get("email"),
    })
    _audit(admin, "create.admin_note", "admin_notes", row.get("note_id"), {"customer_email": str(payload.customer_email)})
    return {"admin_note": row}


@router.post("/admin/credits/adjust")
async def admin_adjust_credits(payload: CreditAdjustmentRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "credits")
    if admin.get("role") not in {"owner", "finance"}:
        raise HTTPException(status_code=403, detail="Only owner or finance can manually adjust credits.")
    owner_email = str(payload.owner_email).lower()
    transaction = _production_insert("credit_transactions", {
        "transaction_id": make_public_id("credit_txn"),
        "owner_email": owner_email,
        "project_id": payload.project_id,
        "amount": payload.amount,
        "reason": payload.reason,
        "created_by_email": admin.get("email"),
    })
    _audit(admin, "adjust.credits", "credit_transactions", transaction.get("transaction_id"), {"owner_email": owner_email, "amount": payload.amount})
    return {"credit_transaction": transaction}


@router.get("/super-admin/me")
async def super_admin_me(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_me(authorization=authorization)


@router.get("/super-admin/overview")
async def super_admin_overview(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_overview(authorization=authorization)


@router.get("/super-admin/customers")
async def super_admin_customers(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_users(q=q, status=status, limit=limit, authorization=authorization)


@router.get("/super-admin/companies")
async def super_admin_companies(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_companies(q=q, status=status, limit=limit, authorization=authorization)


@router.get("/super-admin/projects")
async def super_admin_projects(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_projects(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/uploads")
async def super_admin_uploads(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_uploads(q=q, status=status, project_id=project_id, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/reports")
async def super_admin_reports(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_reports(q=q, status=status, project_id=project_id, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/payments")
async def super_admin_payments(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_payments(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/credit-usage")
async def super_admin_credit_usage(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_credit_usage(q=q, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/support-tickets")
async def super_admin_support_tickets(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_support_tickets(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/activity-logs")
async def super_admin_activity_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_activity_logs(q=q, owner_email=owner_email, limit=limit, authorization=authorization)


@router.get("/super-admin/audit-logs")
async def super_admin_audit_logs(q: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_audit_logs(q=q, limit=limit, authorization=authorization)


@router.get("/super-admin/staff")
async def super_admin_staff(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_staff(q=q, status=status, limit=limit, authorization=authorization)


@router.post("/super-admin/staff")
async def super_admin_create_staff(payload: StaffCreateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_create_staff(payload=payload, authorization=authorization)


@router.patch("/super-admin/staff/{email}")
async def super_admin_update_staff(email: str, payload: StaffUpdateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_update_staff(email=email, payload=payload, authorization=authorization)


@router.patch("/super-admin/customers/{email}/status")
async def super_admin_update_customer_status(email: str, payload: CustomerStatusRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_update_customer_status(email=email, payload=payload, authorization=authorization)


@router.get("/super-admin/notes")
async def super_admin_notes(customer_email: Optional[str] = None, project_id: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_notes(customer_email=customer_email, project_id=project_id, limit=limit, authorization=authorization)


@router.post("/super-admin/notes")
async def super_admin_create_note(payload: AdminNoteRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_create_note(payload=payload, authorization=authorization)


@router.post("/super-admin/support-tickets")
async def super_admin_create_support_ticket(payload: SupportTicketRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_create_support_ticket(payload=payload, authorization=authorization)


@router.patch("/super-admin/support-tickets/{ticket_id}")
async def super_admin_update_support_ticket(ticket_id: str, payload: SupportTicketUpdateRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_update_support_ticket(ticket_id=ticket_id, payload=payload, authorization=authorization)


@router.post("/super-admin/credits/adjust")
async def super_admin_adjust_credits(payload: CreditAdjustmentRequest, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    return await admin_adjust_credits(payload=payload, authorization=authorization)
