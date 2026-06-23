from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, Header, HTTPException

from .saas_common import *
from .services.audit_archive_service import audit_archive_operations_status, retry_audit_archive_item
from .services.operations_health_service import operations_health_status
from .data_lifecycle_routes import DataLifecycleReviewRequest

router = APIRouter(prefix="/api", tags=["SaaS admin"] )

@router.get("/admin/me")
async def admin_me(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "overview", auth_cookie)
    return {"admin": admin, "counts": _admin_counts()}


@router.get("/admin/overview")
async def admin_overview(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "overview", auth_cookie)
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
async def admin_users(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers", auth_cookie)
    rows = _search_rows(_production_rows("users"), q=q, status=status)
    _audit(admin, "view.customers", "users")
    return {"users": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/companies")
async def admin_companies(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers", auth_cookie)
    rows = _search_rows(_production_rows("companies"), q=q, status=status)
    _audit(admin, "view.companies", "companies")
    return {"companies": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/projects")
async def admin_projects(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "projects", auth_cookie)
    rows = _search_rows(_production_rows("projects"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.projects", "projects")
    return {"projects": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/payments")
async def admin_payments(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "payments", auth_cookie)
    payments = _search_rows(_production_rows("payments"), q=q, status=status, owner_email=owner_email)
    sessions = _search_rows(_production_rows("checkout_sessions"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.payments", "payments")
    return {"payments": _limited(payments, limit), "checkout_sessions": _limited(sessions, limit), "total": len(payments) + len(sessions)}


@router.get("/admin/reports")
async def admin_reports(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "reports", auth_cookie)
    rows = _search_rows(_production_rows("reports"), q=q, status=status, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.reports", "reports")
    return {"reports": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/failed-uploads")
async def admin_failed_uploads(q: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "uploads", auth_cookie)
    rows = _search_rows(_failed_upload_rows(), q=q, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.failed_uploads", "uploaded_files")
    return {"failed_uploads": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/credit-usage")
async def admin_credit_usage(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "credits", auth_cookie)
    credits = _search_rows(_production_rows("analysis_credits"), q=q, owner_email=owner_email)
    usage = _search_rows(_production_rows("subscription_usage"), q=q, owner_email=owner_email)
    totals = {
        "credits_total": sum(int(r.get("total_credits") or r.get("amount") or 0) for r in credits),
        "credits_used": sum(int(r.get("used_credits") or max(0, int(r.get("amount") or r.get("total_credits") or 0) - int(r.get("remaining") or r.get("remaining_credits") or 0))) for r in credits),
        "credits_remaining": sum(int(r.get("remaining_credits") or r.get("remaining") or 0) for r in credits),
        "usage_events": len(usage),
    }
    _audit(admin, "view.credits", "analysis_credits")
    return {"analysis_credits": _limited(credits, limit), "subscription_usage": _limited(usage, limit), "totals": totals, "total": len(credits) + len(usage)}


@router.get("/admin/activity-logs")
async def admin_activity_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "activity", auth_cookie)
    rows = _search_rows(_production_rows("activity_logs"), q=q, owner_email=owner_email)
    _audit(admin, "view.activity_logs", "activity_logs")
    return {"activity_logs": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/logs")
async def admin_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_activity_logs(q=q, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/admin/uploads")
async def admin_uploads(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "uploads", auth_cookie)
    rows = _search_rows(_safe_upload_rows(_production_rows("uploaded_files")), q=q, status=status, project_id=project_id, owner_email=owner_email)
    _audit(admin, "view.uploads", "uploaded_files")
    return {"uploads": _limited(rows, limit), "total": len(rows)}


@router.get("/admin/support-tickets")
async def admin_support_tickets(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support", auth_cookie)
    rows = _search_rows(_production_rows("support_tickets"), q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.support_tickets", "support_tickets")
    return {"support_tickets": _limited(rows, limit), "total": len(rows)}


@router.post("/admin/support-tickets")
async def admin_create_support_ticket(payload: SupportTicketRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support", auth_cookie)
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
async def admin_update_support_ticket(ticket_id: str, payload: SupportTicketUpdateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "support", auth_cookie)
    patch = payload.model_dump(exclude_unset=True)
    if payload.internal_note:
        patch["last_internal_note"] = payload.internal_note
        patch["last_internal_note_by"] = admin.get("email")
    row = _production_update("support_tickets", "ticket_id", ticket_id, patch)
    _audit(admin, "update.support_ticket", "support_tickets", ticket_id, patch)
    return {"support_ticket": row}


@router.get("/admin/audit-logs")
async def admin_audit_logs(q: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "audit", auth_cookie)
    rows = _search_rows(_production_rows("audit_logs"), q=q)
    _audit(admin, "view.audit_logs", "audit_logs")
    return {"audit_logs": [redact_audit_row(row) for row in _limited(rows, limit)], "total": len(rows)}


@router.get("/admin/audit-integrity")
async def admin_audit_integrity(limit: int = 2000, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "audit", auth_cookie)
    status = audit_integrity_status(limit=limit)
    _audit(admin, "view.audit_integrity", "audit_logs", metadata={"limit": max(1, min(int(limit or 2000), 10000))})
    return {"audit_integrity": status}


@router.get("/admin/operations-health")
async def admin_operations_health(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    """Owner/operator-safe cross-service health summary without secrets or tenant data."""
    admin = await require_super_admin_user(authorization, "operations", auth_cookie)
    status = operations_health_status()
    _audit(admin, "view.operations_health", "operations_health", metadata={"status": status.get("status"), "incident_count": len(status.get("incidents") or [])})
    return {"operations_health": status}


@router.get("/admin/audit-archive")
async def admin_audit_archive(limit: int = 100, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    """Owner/staff-safe archive queue health; never exposes webhook configuration."""
    admin = await require_super_admin_user(authorization, "audit", auth_cookie)
    status = audit_archive_operations_status(limit=limit)
    _audit(admin, "view.audit_archive", "audit_archive_outbox", metadata={"limit": max(1, min(int(limit or 100), 1000))})
    return {"audit_archive": status}


@router.post("/admin/audit-archive/{archive_id}/retry")
async def admin_retry_audit_archive(
    archive_id: str,
    payload: AuditArchiveRetryRequest | None = None,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    """Explicit owner-only recovery for a reviewed archive delivery failure."""
    admin = await require_super_admin_user(authorization, "audit", auth_cookie)
    if _normalize_staff_role(admin.get("role")) != "owner":
        raise HTTPException(status_code=403, detail="Only owner can retry audit archive delivery.")
    row = retry_audit_archive_item(
        archive_id=archive_id,
        actor=admin,
        reset_attempts=bool(payload.reset_attempts if payload else False),
    )
    _audit(admin, "retry.audit_archive", "audit_archive_outbox", archive_id, {"reset_attempts": bool(payload.reset_attempts if payload else False)})
    return {"audit_archive_item": row}


@router.get("/admin/staff")
async def admin_staff(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff", auth_cookie)
    rows = [
        row for row in _search_rows(_production_rows("users"), q=q, status=status)
        if _normalize_staff_role(row.get("role")) in SUPER_ADMIN_ROLES
    ]
    _audit(admin, "view.staff", "users")
    return {"staff": _limited(rows, limit), "total": len(rows), "roles": sorted(SUPER_ADMIN_ROLES)}


@router.post("/admin/staff")
async def admin_create_staff(payload: StaffCreateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff", auth_cookie)
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
async def admin_update_staff(email: str, payload: StaffUpdateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "staff", auth_cookie)
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
async def admin_update_customer_status(email: str, payload: CustomerStatusRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "customers", auth_cookie)
    email = email.strip().lower()
    target_rows = _production_rows("users", email=email, limit=1)
    target = target_rows[0] if target_rows else None
    if target and _normalize_staff_role(target.get("role")) in SUPER_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Staff accounts must be managed through the staff-management endpoint.",
        )
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
async def admin_notes(customer_email: Optional[str] = None, project_id: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "notes", auth_cookie)
    rows = _production_rows("admin_notes", owner_email=customer_email, project_id=project_id)
    _audit(admin, "view.admin_notes", "admin_notes")
    return {"admin_notes": _limited(rows, limit), "total": len(rows)}


@router.post("/admin/notes")
async def admin_create_note(payload: AdminNoteRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "notes", auth_cookie)
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
async def admin_adjust_credits(payload: CreditAdjustmentRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    admin = await require_super_admin_user(authorization, "credits", auth_cookie)
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




@router.get("/admin/data-lifecycle/requests")
async def admin_data_lifecycle_requests(
    q: Optional[str] = None,
    status: Optional[str] = None,
    owner_email: Optional[str] = None,
    request_type: Optional[str] = None,
    limit: int = 200,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    """Owner review queue for privacy/export/erasure requests.

    This view intentionally omits any generated export payload or storage path.
    """
    from .services.data_lifecycle_service import admin_safe_row

    admin = await require_super_admin_user(authorization, "privacy", auth_cookie)
    rows = _production_rows("data_lifecycle_requests")
    if request_type:
        rows = [row for row in rows if str(row.get("request_type") or "").lower() == str(request_type).lower()]
    rows = _search_rows(rows, q=q, status=status, owner_email=owner_email)
    _audit(admin, "view.privacy_requests", "data_lifecycle_requests")
    return {"requests": [admin_safe_row(row) for row in _limited(rows, limit)], "total": len(rows)}


@router.patch("/admin/data-lifecycle/requests/{request_id}")
async def admin_review_data_lifecycle_request(
    request_id: str,
    payload: DataLifecycleReviewRequest,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    from datetime import datetime, timezone
    from .services.data_lifecycle_service import REVIEW_STATUSES, admin_safe_row

    admin = await require_super_admin_user(authorization, "privacy", auth_cookie)
    rows = _production_rows("data_lifecycle_requests", lifecycle_request_id=request_id)
    request = rows[0] if rows else None
    if not request:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Privacy request not found."})
    current_status = str(request.get("status") or "").lower()
    if current_status in {"cancelled", "rejected", "completed"}:
        raise HTTPException(status_code=409, detail={"error": "terminal_request", "message": "Terminal privacy requests cannot be reviewed again."})
    next_status = str(payload.status or "").lower()
    if next_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail={"error": "invalid_review_status", "message": "Review status is invalid."})
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    patch: Dict[str, Any] = {
        "status": next_status,
        "reviewed_at": now,
        "reviewed_by": admin.get("email"),
        "review_note": str(payload.review_note or "").strip()[:2000] or None,
        "updated_at": now,
    }
    if request.get("request_type") == "erasure":
        patch["scheduled_purge_at"] = request.get("grace_expires_at") if next_status == "approved" else None
    updated = _production_update("data_lifecycle_requests", "lifecycle_request_id", request_id, patch)
    action = "schedule.delete_request" if next_status == "approved" and request.get("request_type") == "erasure" else "update.privacy_request"
    _audit(admin, action, "data_lifecycle_requests", request_id, {
        "owner_email": request.get("requester_email"),
        "request_type": request.get("request_type"),
        "status": next_status,
        "scope": request.get("scope"),
        "project_id": request.get("project_id"),
    })
    return {"request": admin_safe_row(updated), "automatic_physical_purge": False}
