from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, Header

from .saas_common import *
from .data_lifecycle_routes import DataLifecycleReviewRequest
from . import saas_admin_routes as admin_routes

router = APIRouter(prefix="/api", tags=["SaaS super admin"] )

@router.get("/super-admin/me")
async def super_admin_me(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_me(authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/overview")
async def super_admin_overview(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_overview(authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/customers")
async def super_admin_customers(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_users(q=q, status=status, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/companies")
async def super_admin_companies(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_companies(q=q, status=status, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/projects")
async def super_admin_projects(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_projects(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/uploads")
async def super_admin_uploads(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_uploads(q=q, status=status, project_id=project_id, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/reports")
async def super_admin_reports(q: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_reports(q=q, status=status, project_id=project_id, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/payments")
async def super_admin_payments(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_payments(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/credit-usage")
async def super_admin_credit_usage(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_credit_usage(q=q, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/support-tickets")
async def super_admin_support_tickets(q: Optional[str] = None, status: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_support_tickets(q=q, status=status, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/activity-logs")
async def super_admin_activity_logs(q: Optional[str] = None, owner_email: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_activity_logs(q=q, owner_email=owner_email, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/audit-logs")
async def super_admin_audit_logs(q: Optional[str] = None, limit: int = 300, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_audit_logs(q=q, limit=limit, authorization=authorization, auth_cookie=auth_cookie)

@router.get("/super-admin/audit-integrity")
async def super_admin_audit_integrity(limit: int = 2000, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_audit_integrity(limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/operations-health")
async def super_admin_operations_health(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_operations_health(authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/audit-archive")
async def super_admin_audit_archive(limit: int = 100, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_audit_archive(limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.post("/super-admin/audit-archive/{archive_id}/retry")
async def super_admin_retry_audit_archive(
    archive_id: str,
    payload: AuditArchiveRetryRequest | None = None,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    return await admin_routes.admin_retry_audit_archive(
        archive_id=archive_id,
        payload=payload,
        authorization=authorization,
        auth_cookie=auth_cookie,
    )


@router.get("/super-admin/staff")
async def super_admin_staff(q: Optional[str] = None, status: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_staff(q=q, status=status, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.post("/super-admin/staff")
async def super_admin_create_staff(payload: StaffCreateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_create_staff(payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.patch("/super-admin/staff/{email}")
async def super_admin_update_staff(email: str, payload: StaffUpdateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_update_staff(email=email, payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.patch("/super-admin/customers/{email}/status")
async def super_admin_update_customer_status(email: str, payload: CustomerStatusRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_update_customer_status(email=email, payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/notes")
async def super_admin_notes(customer_email: Optional[str] = None, project_id: Optional[str] = None, limit: int = 200, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_notes(customer_email=customer_email, project_id=project_id, limit=limit, authorization=authorization, auth_cookie=auth_cookie)


@router.post("/super-admin/notes")
async def super_admin_create_note(payload: AdminNoteRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_create_note(payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.post("/super-admin/support-tickets")
async def super_admin_create_support_ticket(payload: SupportTicketRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_create_support_ticket(payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.patch("/super-admin/support-tickets/{ticket_id}")
async def super_admin_update_support_ticket(ticket_id: str, payload: SupportTicketUpdateRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_update_support_ticket(ticket_id=ticket_id, payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.post("/super-admin/credits/adjust")
async def super_admin_adjust_credits(payload: CreditAdjustmentRequest, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    return await admin_routes.admin_adjust_credits(payload=payload, authorization=authorization, auth_cookie=auth_cookie)


@router.get("/super-admin/data-lifecycle/requests")
async def super_admin_data_lifecycle_requests(
    q: Optional[str] = None,
    status: Optional[str] = None,
    owner_email: Optional[str] = None,
    request_type: Optional[str] = None,
    limit: int = 200,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    return await admin_routes.admin_data_lifecycle_requests(
        q=q,
        status=status,
        owner_email=owner_email,
        request_type=request_type,
        limit=limit,
        authorization=authorization,
        auth_cookie=auth_cookie,
    )


@router.patch("/super-admin/data-lifecycle/requests/{request_id}")
async def super_admin_review_data_lifecycle_request(
    request_id: str,
    payload: DataLifecycleReviewRequest,
    authorization: Optional[str] = Header(None),
    auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE),
) -> Dict[str, Any]:
    return await admin_routes.admin_review_data_lifecycle_request(
        request_id=request_id,
        payload=payload,
        authorization=authorization,
        auth_cookie=auth_cookie,
    )
