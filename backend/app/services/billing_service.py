from __future__ import annotations

import json
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from ..auth_dependencies import CurrentUser, local_store_enabled
from ..access_control import can_access_project_scope
from ..production_store import ProductionStoreError, call_rpc, first_update, insert_row, is_configured, select_one, select_rows, uuid_like
from ..security_runtime import bool_env, production_security_enabled


PLAN_LIMITS = {
    "single": {"limit": 1, "kind": "one_time"},
    "plus": {"limit": 5, "kind": "subscription"},
    "pro": {"limit": 20, "kind": "subscription"},
}


PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _safe_nonempty(value: Any, max_length: int = 160) -> Optional[str]:
    normalized = str(value or "").strip()
    return normalized[:max_length] if normalized else None


def _event_max_attempts() -> int:
    try:
        value = int(os.getenv("DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS", str(PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT)))
    except (TypeError, ValueError):
        value = PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT
    return max(1, min(value, 20))


def _event_fingerprint(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _email_fingerprint(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_billing_status(user: CurrentUser) -> Dict[str, Any]:
    if can_access_project_scope(user.role, "projects"):
        return {"plan_name": "admin", "status": "active", "monthly_project_limit": None, "used_project_count": 0, "remaining": None, "unlimited": True}
    subscriptions = _active_subscriptions(user)
    credits = _active_credits(user)
    if subscriptions:
        sub = subscriptions[0]
        limit = int(sub.get("monthly_project_limit") or PLAN_LIMITS.get(str(sub.get("plan_name") or "").lower(), {}).get("limit") or 0)
        used = int(sub.get("used_project_count") or 0)
        return {
            "plan_name": sub.get("plan_name"),
            "status": sub.get("status"),
            "monthly_project_limit": limit,
            "used_project_count": used,
            "remaining": max(0, limit - used),
            "current_period_start": sub.get("current_period_start"),
            "current_period_end": sub.get("current_period_end"),
            "unlimited": False,
            "credits": credits,
        }
    remaining = sum(int(row.get("remaining") or row.get("remaining_credits") or 0) for row in credits)
    return {
        "plan_name": "single" if remaining else "none",
        "status": "active" if remaining else "inactive",
        "monthly_project_limit": 0,
        "used_project_count": 0,
        "remaining": remaining,
        "unlimited": False,
        "credits": credits,
    }


def get_usage(user: CurrentUser) -> Dict[str, Any]:
    status = get_billing_status(user)
    return {
        "plan_name": status.get("plan_name"),
        "used": status.get("used_project_count") or 0,
        "limit": status.get("monthly_project_limit"),
        "remaining": status.get("remaining"),
        "unlimited": status.get("unlimited"),
        "credits": status.get("credits") or [],
    }


def ensure_analysis_available(user: CurrentUser, project_id: str) -> Dict[str, Any]:
    usage = get_usage(user)
    if usage.get("unlimited"):
        return {"allowed": True, "mode": "admin_unlimited", "usage": usage}
    remaining = usage.get("remaining")
    if remaining is None or int(remaining) > 0:
        return {"allowed": True, "mode": "subscription_or_credit", "usage": usage}
    raise HTTPException(
        status_code=402,
        detail={
            "error": "payment_required",
            "message": "No project review credits are available. Upgrade plan or buy a one-time project review.",
            "usage": usage,
            "project_id": project_id,
        },
    )


def consume_after_success(user: CurrentUser, project_id: str, job_id: str) -> Dict[str, Any]:
    """Consume one analysis entitlement exactly once for a completed job.

    In a configured Supabase deployment this delegates to the v1.4.18 RPC,
    which locks the job row and writes a unique usage ledger entry in the same
    transaction as the subscription/credit update. Local development keeps the
    prior in-memory fallback for convenience.
    """
    if is_configured() and uuid_like(job_id):
        try:
            result = call_rpc(
                "consume_analysis_usage_once",
                {
                    "p_job_id": job_id,
                    "p_owner_email": user.email,
                    "p_is_unlimited": bool(can_access_project_scope(user.role, "projects")),
                },
            )
        except ProductionStoreError as exc:
            message = str(exc)
            migration_missing = "consume_analysis_usage_once" in message and ("does not exist" in message or "PGRST202" in message)
            if production_security_enabled() or not migration_missing:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "billing_usage_rpc_unavailable",
                        "message": "Atomic analysis usage accounting is unavailable. Apply the v1.4.18 database migration before retrying the job.",
                    },
                ) from exc
        else:
            if not isinstance(result, dict):
                raise HTTPException(status_code=503, detail={"error": "billing_usage_rpc_invalid", "message": "Atomic usage accounting returned an invalid response."})
            if result.get("error") == "payment_required":
                raise HTTPException(status_code=402, detail={"error": "payment_required", "message": "Project review completed, but no usable credit record was found."})
            if result.get("consumed") and not result.get("already_consumed"):
                mode = str(result.get("mode") or "usage")
                _log_activity(user, project_id, f"billing.{mode}_usage_consumed", {"job_id": job_id, "usage_ledger_id": result.get("ledger_id")})
            return result

    # Local/non-production compatibility fallback. Production must use the RPC.
    if can_access_project_scope(user.role, "projects"):
        return {"consumed": False, "already_consumed": False, "mode": "admin_unlimited"}
    subscriptions = _active_subscriptions(user)
    if subscriptions:
        sub = subscriptions[0]
        limit = int(sub.get("monthly_project_limit") or PLAN_LIMITS.get(str(sub.get("plan_name") or "").lower(), {}).get("limit") or 0)
        used = int(sub.get("used_project_count") or 0)
        if limit and used < limit:
            patch = {"used_project_count": used + 1, "updated_at": datetime.utcnow().isoformat()}
            updated = _update_by_id("subscriptions", sub, patch)
            _log_activity(user, project_id, "billing.subscription_usage_consumed", {"job_id": job_id, "subscription_id": sub.get("id")})
            return {"consumed": True, "already_consumed": False, "mode": "subscription", "subscription": updated or sub}
    for credit in _active_credits(user):
        remaining = int(credit.get("remaining") or credit.get("remaining_credits") or 0)
        if remaining > 0:
            amount = int(credit.get("amount") or credit.get("total_credits") or remaining)
            used_credits = int(credit.get("used_credits") or 0)
            total_credits = int(credit.get("total_credits") or credit.get("amount") or remaining)
            patch = {
                "remaining": remaining - 1,
                "remaining_credits": remaining - 1,
                "used_credits": min(total_credits, used_credits + 1),
                "total_credits": total_credits,
            }
            updated = _update_by_id("analysis_credits", credit, patch)
            _log_activity(user, project_id, "billing.credit_consumed", {"job_id": job_id, "credit_id": credit.get("id"), "amount": amount})
            return {"consumed": True, "already_consumed": False, "mode": "credit", "credit": updated or credit}
    raise HTTPException(status_code=402, detail={"error": "payment_required", "message": "Project review completed, but no usable credit record was found."})


def create_subscription_checkout(user: CurrentUser, plan: str, success_url: Optional[str], cancel_url: Optional[str]) -> Dict[str, Any]:
    plan = str(plan or "").lower()
    if plan not in {"plus", "pro"}:
        raise HTTPException(status_code=400, detail={"error": "invalid_plan", "message": "Subscription checkout supports Plus and Pro."})
    return _create_checkout(user=user, plan=plan, mode="subscription", success_url=success_url, cancel_url=cancel_url)


def create_one_time_checkout(user: CurrentUser, project_id: Optional[str], success_url: Optional[str], cancel_url: Optional[str]) -> Dict[str, Any]:
    return _create_checkout(user=user, plan="single", mode="payment", project_id=project_id, success_url=success_url, cancel_url=cancel_url)


def create_checkout_session(user: CurrentUser, plan: str, project_id: Optional[str], success_url: Optional[str], cancel_url: Optional[str]) -> Dict[str, Any]:
    plan = str(plan or "single").lower()
    mode = "payment" if plan == "single" else "subscription"
    return _create_checkout(user=user, plan=plan, mode=mode, project_id=project_id, success_url=success_url, cancel_url=cancel_url)


def handle_webhook(raw_body: bytes, signature: Optional[str], provider_hint: Optional[str] = None) -> Dict[str, Any]:
    provider = str(provider_hint or _payment_provider()).strip().lower()
    if provider == "lemonsqueezy":
        return _handle_lemon_webhook(raw_body, signature)
    raise HTTPException(status_code=400, detail={"error": "unsupported_payment_provider", "message": "Only Lemon Squeezy webhooks are supported."})


def _create_checkout(
    *,
    user: CurrentUser,
    plan: str,
    mode: str,
    project_id: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail={"error": "invalid_plan", "message": f"Unsupported plan: {plan}"})
    if _payment_provider() == "lemonsqueezy" and _lemon_ready():
        return _create_lemon_checkout(user=user, plan=plan, mode=mode, project_id=project_id, success_url=success_url, cancel_url=cancel_url)
    if not production_security_enabled() and bool_env("DEVBAREUN_ENABLE_MOCK_PAYMENT", False):
        return {"mode": "mock_disabled_by_default", "checkout_url": None, "plan": plan}
    raise HTTPException(status_code=503, detail={"error": "lemon_not_configured", "message": "Lemon Squeezy checkout is not configured. Set LEMON_SQUEEZY_API_KEY, LEMON_SQUEEZY_STORE_ID and variant IDs."})


def _active_subscriptions(user: CurrentUser) -> List[Dict[str, Any]]:
    if not is_configured():
        if local_store_enabled():
            from ..saas_store import list_rows

            rows = list_rows("subscriptions", owner_email=user.email)
        elif production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Supabase PostgreSQL is required for billing status."})
        else:
            rows = []
    else:
        rows = select_rows("subscriptions", {"owner_email": user.email}, limit=100)

    now = _now()
    active: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("status") or "").lower() not in {"active", "trialing"}:
            continue
        period_end = _parse_timestamp(row.get("current_period_end"))
        # A provider may be late delivering an expiration event. Do not keep
        # granting monthly access merely because the stored status says active.
        if period_end and period_end <= now:
            continue
        active.append(row)
    active.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
    return active


def _active_credits(user: CurrentUser) -> List[Dict[str, Any]]:
    if not is_configured():
        if local_store_enabled():
            from ..saas_store import list_rows

            rows = list_rows("analysis_credits", owner_email=user.email)
        else:
            rows = []
    else:
        rows = select_rows("analysis_credits", {"owner_email": user.email}, limit=200)

    now = _now()
    active: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("status") or "active").lower() != "active":
            continue
        if int(row.get("remaining") or row.get("remaining_credits") or 0) <= 0:
            continue
        expires_at = _parse_timestamp(row.get("expires_at"))
        if expires_at and expires_at <= now:
            continue
        active.append(row)
    return active


def _update_by_id(table: str, row: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any] | None:
    row_id = row.get("id")
    if is_configured() and row_id:
        return first_update(table, {"id": row_id}, patch)
    if local_store_enabled():
        from ..saas_store import update_one

        key = "id" if row.get("id") else f"{table[:-1]}_id"
        return update_one(table, key, row.get(key), patch)
    return None


def _record_checkout_session(
    user: CurrentUser,
    *,
    checkout_id: str,
    plan: str,
    project_id: Optional[str],
    provider_session_id: Optional[str],
    checkout_url: Optional[str],
) -> None:
    if not is_configured():
        return
    payload = {
        "checkout_id": checkout_id,
        "plan_code": plan,
        "project_id": _safe_nonempty(project_id, 120),
        "user_id": user.id if uuid_like(user.id) else (user.auth_user_id if uuid_like(user.auth_user_id) else None),
        "owner_email": user.email,
        "customer_email": user.email,
        "provider_checkout_session_id": provider_session_id,
        "checkout_url": checkout_url,
        "status": "provider_checkout_created",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    try:
        insert_row("checkout_sessions", payload)
    except ProductionStoreError as exc:
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "checkout_persistence_unavailable", "message": "Checkout session could not be recorded."}) from exc


def _insert_payment(user: CurrentUser, plan: str, session: Dict[str, Any], project_id: Optional[str], checkout_id: Optional[str]) -> None:
    payload = {
        "user_id": user.id if uuid_like(user.id) else (user.auth_user_id if uuid_like(user.auth_user_id) else None),
        "owner_email": user.email,
        "project_id": project_id if uuid_like(str(project_id or "")) else None,
        "provider": "lemonsqueezy",
        "payment_provider": "lemonsqueezy",
        "provider_session_id": session.get("id"),
        "provider_checkout_session_id": session.get("id"),
        "checkout_id": checkout_id,
        "plan_name": plan,
        "plan_code": plan,
        "amount": None,
        "currency": os.getenv("LEMON_SQUEEZY_CURRENCY", "usd"),
        "status": "checkout_created",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if is_configured():
        try:
            insert_row("payments", payload)
        except ProductionStoreError as exc:
            if production_security_enabled():
                raise HTTPException(status_code=503, detail={"error": "checkout_payment_record_unavailable", "message": "Checkout payment record could not be created."}) from exc


def _claim_payment_event(
    event_id: str,
    event_type: str,
    payload_summary: Dict[str, Any],
    *,
    checkout_id: Optional[str],
    plan_name: Optional[str],
    payload_sha256: str,
) -> Dict[str, Any]:
    if not is_configured():
        return {"claimed": True, "state": "local"}
    try:
        result = call_rpc(
            "claim_payment_webhook_event",
            {
                "p_provider_event_id": event_id,
                "p_provider": "lemonsqueezy",
                "p_event_type": event_type,
                "p_payload": payload_summary,
                "p_payload_sha256": payload_sha256,
                "p_checkout_id": checkout_id,
                "p_plan_name": plan_name,
                "p_max_attempts": _event_max_attempts(),
            },
        )
    except ProductionStoreError as exc:
        message = str(exc)
        missing = "claim_payment_webhook_event" in message and ("does not exist" in message or "PGRST202" in message)
        if production_security_enabled() or not missing:
            raise HTTPException(status_code=503, detail={"error": "payment_event_claim_unavailable", "message": "Atomic payment event handling is unavailable. Apply the v1.4.31 migration."}) from exc
        if select_one("payment_events", {"provider_event_id": event_id}):
            return {"claimed": False, "state": "duplicate_processed"}
        insert_row("payment_events", {"provider_event_id": event_id, "event_type": event_type, "payload": payload_summary, "processed_at": _now_iso()})
        return {"claimed": True, "state": "legacy"}
    if not isinstance(result, dict):
        raise HTTPException(status_code=503, detail={"error": "payment_event_claim_invalid", "message": "Atomic payment event handling returned an invalid response."})
    return result


def _complete_payment_event(event_id: str, *, success: bool, outcome: Dict[str, Any], error_code: Optional[str] = None) -> None:
    if not is_configured():
        return
    try:
        call_rpc(
            "complete_payment_webhook_event",
            {
                "p_provider_event_id": event_id,
                "p_success": bool(success),
                "p_outcome": outcome,
                "p_error_code": _safe_nonempty(error_code, 80),
            },
        )
    except ProductionStoreError as exc:
        message = str(exc)
        missing = "complete_payment_webhook_event" in message and ("does not exist" in message or "PGRST202" in message)
        if production_security_enabled() or not missing:
            raise HTTPException(status_code=503, detail={"error": "payment_event_completion_unavailable", "message": "Payment event completion could not be recorded."}) from exc


def _checkout_lookup_filters(checkout_id: Optional[str], provider_session_id: Optional[str]) -> List[Dict[str, Any]]:
    filters: List[Dict[str, Any]] = []
    if checkout_id:
        filters.append({"checkout_id": checkout_id})
    if provider_session_id:
        filters.append({"provider_checkout_session_id": provider_session_id})
    return filters


def _mark_checkout_and_payment(
    *,
    checkout_id: Optional[str],
    provider_session_id: Optional[str],
    status: str,
    event_id: str,
    provider_order_id: Optional[str] = None,
    provider_subscription_id: Optional[str] = None,
    failure_code: Optional[str] = None,
) -> None:
    if not is_configured():
        return
    now = _now_iso()
    checkout_patch = {
        "status": status,
        "last_event_id": event_id,
        "provider_order_id": provider_order_id,
        "failure_code": failure_code,
        "paid_at": now if status in {"paid", "subscription_active"} else None,
        "updated_at": now,
    }
    payment_patch = {
        "status": status,
        "last_provider_event_id": event_id,
        "provider_order_id": provider_order_id,
        "provider_subscription_id": provider_subscription_id,
        "failure_reason_code": failure_code,
        "paid_at": now if status in {"paid", "subscription_active"} else None,
        "updated_at": now,
    }
    for filters in _checkout_lookup_filters(checkout_id, provider_session_id):
        try:
            first_update("checkout_sessions", filters, checkout_patch)
        except ProductionStoreError:
            continue
        break
    for filters in _checkout_lookup_filters(checkout_id, provider_session_id):
        try:
            first_update("payments", filters, payment_patch)
        except ProductionStoreError:
            continue
        break


def _provider_period(subscription_obj: Dict[str, Any], existing: Optional[Dict[str, Any]]) -> tuple[datetime, datetime]:
    attrs = subscription_obj.get("attributes") or {}
    end = _parse_timestamp(attrs.get("renews_at") or attrs.get("ends_at") or attrs.get("trial_ends_at"))
    start = _parse_timestamp(attrs.get("created_at"))
    if end and not start:
        start = end - timedelta(days=30)
    if not end:
        prior_end = _parse_timestamp((existing or {}).get("current_period_end"))
        if prior_end and prior_end > _now():
            end = prior_end
            start = _parse_timestamp((existing or {}).get("current_period_start")) or (end - timedelta(days=30))
        else:
            start = _now()
            end = start + timedelta(days=30)
    return start or (end - timedelta(days=30)), end


def _upsert_subscription(user_id: Optional[str], email: Optional[str], plan: str, obj: Dict[str, Any], status: str) -> Dict[str, Any] | None:
    if not is_configured():
        return None
    provider_subscription_id = obj.get("subscription") or obj.get("id")
    existing = select_one("subscriptions", {"provider_subscription_id": provider_subscription_id}) if provider_subscription_id else None
    period_start, period_end = _provider_period(obj, existing)
    prior_end = _parse_timestamp((existing or {}).get("current_period_end"))
    # Monthly usage resets only when the provider period actually advances.
    usage = int((existing or {}).get("used_project_count") or 0)
    if prior_end and period_end > prior_end:
        usage = 0
    payload = {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "plan_name": plan,
        "plan_code": plan,
        "status": status,
        "monthly_project_limit": PLAN_LIMITS[plan]["limit"],
        "used_project_count": usage,
        "current_period_start": period_start.isoformat(),
        "current_period_end": period_end.isoformat(),
        "provider": "lemonsqueezy",
        "provider_customer_id": obj.get("customer"),
        "provider_subscription_id": provider_subscription_id,
        "updated_at": _now_iso(),
    }
    if existing:
        return first_update("subscriptions", {"id": existing["id"]}, payload) or existing
    payload["created_at"] = _now_iso()
    return insert_row("subscriptions", payload)


def _grant_credit(
    user_id: Optional[str],
    email: Optional[str],
    project_id: Optional[str],
    source: str,
    *,
    event_id: str,
    checkout_id: Optional[str],
    provider_order_id: Optional[str],
) -> Dict[str, Any] | None:
    if not is_configured():
        return None
    existing_credit = select_one("analysis_credits", {"source_event_id": event_id})
    if existing_credit:
        return existing_credit
    insert_payload = {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "project_id": project_id if uuid_like(str(project_id or "")) else None,
        "source": source,
        "source_event_id": event_id,
        "checkout_id": checkout_id,
        "provider_order_id": provider_order_id,
        "credit_type": "single_project",
        "amount": 1,
        "remaining": 1,
        "total_credits": 1,
        "used_credits": 0,
        "remaining_credits": 1,
        "status": "active",
        "expires_at": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    credit = insert_row("analysis_credits", insert_payload)
    _mark_checkout_and_payment(
        checkout_id=checkout_id,
        provider_session_id=None,
        status="paid",
        event_id=event_id,
        provider_order_id=provider_order_id,
    )
    return credit


def _revoke_unspent_credit(*, checkout_id: Optional[str], provider_order_id: Optional[str], event_id: str) -> Dict[str, Any]:
    if not is_configured():
        return {"revoked": False, "reason": "local"}
    credit = None
    if provider_order_id:
        credit = select_one("analysis_credits", {"provider_order_id": provider_order_id})
    if not credit and checkout_id:
        credit = select_one("analysis_credits", {"checkout_id": checkout_id})
    if not credit:
        return {"revoked": False, "reason": "credit_not_found"}
    remaining = int(credit.get("remaining") or credit.get("remaining_credits") or 0)
    used = int(credit.get("used_credits") or 0)
    if used > 0 or remaining <= 0:
        _update_by_id("analysis_credits", credit, {"status": "refund_review_required", "updated_at": _now_iso()})
        return {"revoked": False, "reason": "credit_already_used_or_empty"}
    _update_by_id("analysis_credits", credit, {"status": "refunded", "remaining": 0, "remaining_credits": 0, "updated_at": _now_iso()})
    _mark_checkout_and_payment(checkout_id=checkout_id, provider_session_id=None, status="refunded", event_id=event_id, provider_order_id=provider_order_id)
    return {"revoked": True, "credit_id": credit.get("id")}


def get_checkout_status(user: CurrentUser, checkout_id: str) -> Dict[str, Any]:
    normalized = _safe_nonempty(checkout_id, 120)
    if not normalized:
        raise HTTPException(status_code=400, detail={"error": "invalid_checkout_id", "message": "Checkout ID is required."})
    if not is_configured():
        raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Checkout status requires the production database."})
    checkout = select_one("checkout_sessions", {"checkout_id": normalized})
    if not checkout:
        raise HTTPException(status_code=404, detail={"error": "checkout_not_found", "message": "Checkout session was not found."})
    if not can_access_project_scope(user.role, "payments") and str(checkout.get("owner_email") or "").lower() != str(user.email or "").lower():
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Checkout belongs to another customer."})
    payment = select_one("payments", {"checkout_id": normalized})
    return {
        "checkout": {
            "checkout_id": checkout.get("checkout_id"),
            "plan_code": checkout.get("plan_code"),
            "status": checkout.get("status"),
            "created_at": checkout.get("created_at"),
            "updated_at": checkout.get("updated_at"),
            "paid_at": checkout.get("paid_at"),
            "failure_code": checkout.get("failure_code"),
        },
        "payment": {
            "status": (payment or {}).get("status"),
            "paid_at": (payment or {}).get("paid_at"),
            "updated_at": (payment or {}).get("updated_at"),
        } if payment else None,
        "poll_after_seconds": 5 if str(checkout.get("status") or "").lower() in {"provider_checkout_created", "payment_pending"} else None,
    }


def _log_activity(user: CurrentUser, project_id: Optional[str], action: str, metadata: Dict[str, Any]) -> None:
    if not is_configured():
        return
    try:
        insert_row("activity_logs", {
            "user_id": user.id if uuid_like(user.id) else user.auth_user_id,
            "owner_email": user.email,
            "project_id": project_id if uuid_like(str(project_id or "")) else None,
            "action": action,
            "metadata": metadata,
            "created_at": _now_iso(),
        })
    except ProductionStoreError:
        return


def _payment_provider() -> str:
    provider = os.getenv("DEVBAREUN_PAYMENT_PROVIDER", "").strip().lower()
    if provider:
        return provider
    if os.getenv("LEMON_SQUEEZY_API_KEY") and os.getenv("LEMON_SQUEEZY_STORE_ID"):
        return "lemonsqueezy"
    return "lemonsqueezy"


def _lemon_variant_env(plan: str) -> str:
    return {
        "single": "LEMON_SQUEEZY_SINGLE_VARIANT_ID",
        "plus": "LEMON_SQUEEZY_PLUS_VARIANT_ID",
        "pro": "LEMON_SQUEEZY_PRO_VARIANT_ID",
    }[plan]


def _lemon_ready() -> bool:
    return bool(os.getenv("LEMON_SQUEEZY_API_KEY") and os.getenv("LEMON_SQUEEZY_STORE_ID"))


def _create_lemon_checkout(
    *,
    user: CurrentUser,
    plan: str,
    mode: str,
    project_id: Optional[str],
    success_url: Optional[str],
    cancel_url: Optional[str],
) -> Dict[str, Any]:
    variant_id = os.getenv(_lemon_variant_env(plan))
    if not variant_id:
        raise HTTPException(status_code=503, detail={"error": "lemon_variant_missing", "message": f"{_lemon_variant_env(plan)} is required."})

    checkout_id = str(uuid4())
    success = _append_checkout_id(
        _safe_checkout_url(success_url or f"{_base_url()}/workspace/?view=payment-success"),
        checkout_id,
    )
    cancel = _append_checkout_id(
        _safe_checkout_url(cancel_url or f"{_base_url()}/workspace/?view=payment-failed"),
        checkout_id,
    )
    metadata = {
        "checkout_id": checkout_id,
        "plan": str(plan),
        "user_id": str(user.id or "guest"),
        "auth_user_id": str(user.auth_user_id or "guest"),
        "email": str(user.email),
        "project_id": str(project_id or "none"),
        "mode": str(mode),
    }
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "product_options": {
                    "redirect_url": success,
                    "receipt_button_text": "Open DevBareun",
                    "receipt_link_url": success,
                    "enabled_variants": [int(variant_id) if str(variant_id).isdigit() else variant_id],
                },
                "checkout_options": {
                    "embed": False,
                    "media": True,
                    "logo": True,
                    "desc": True,
                    "subscription_preview": True,
                },
                "checkout_data": {
                    "email": user.email,
                    "custom": metadata,
                },
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(os.getenv("LEMON_SQUEEZY_STORE_ID"))}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }
    try:
        checkout = _lemon_post("/v1/checkouts", payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "lemon_checkout_failed", "message": "Lemon Squeezy checkout could not be created. Please verify billing configuration and try again."}) from exc

    attrs = checkout.get("data", {}).get("attributes", {})
    session = {"id": checkout.get("data", {}).get("id"), "url": attrs.get("url")}
    _record_checkout_session(
        user,
        checkout_id=checkout_id,
        plan=plan,
        project_id=project_id,
        provider_session_id=session.get("id"),
        checkout_url=session.get("url"),
    )
    _insert_payment(user, plan, session, project_id, checkout_id)
    return {
        "checkout_url": attrs.get("url"),
        "session_id": session["id"],
        "checkout_id": checkout_id,
        "cancel_url": cancel,
        "mode": mode,
        "plan": plan,
        "provider": "lemonsqueezy",
    }


def _checkout_owner_context(checkout_id: Optional[str]) -> Dict[str, Any]:
    """Resolve server-created checkout context without trusting webhook custom data.

    Lemon Squeezy custom data is used for correlation, but the owner, project
    and plan become authoritative only when they match the checkout record that
    DevBareun created before redirecting a customer to the provider.
    """
    if not checkout_id or not is_configured():
        return {}
    try:
        checkout = select_one("checkout_sessions", {"checkout_id": checkout_id})
    except ProductionStoreError:
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "checkout_lookup_unavailable", "message": "Checkout ownership could not be verified."})
        return {}
    if not checkout:
        if production_security_enabled():
            raise HTTPException(status_code=409, detail={"error": "checkout_not_found", "message": "The signed payment event does not match a DevBareun checkout."})
        return {}
    return {
        "owner_email": _safe_nonempty(checkout.get("owner_email") or checkout.get("customer_email"), 320),
        "user_id": _safe_nonempty(checkout.get("user_id"), 80),
        "project_id": _safe_nonempty(checkout.get("project_id"), 120),
        "plan": _safe_nonempty(checkout.get("plan_code"), 32),
    }


def _handle_lemon_webhook(raw_body: bytes, signature: Optional[str]) -> Dict[str, Any]:
    secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET")
    if secret:
        if not signature:
            raise HTTPException(status_code=400, detail={"error": "missing_signature", "message": "Missing X-Signature header."})
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, signature):
            raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid Lemon Squeezy signature."})
    elif production_security_enabled():
        raise HTTPException(status_code=503, detail={"error": "lemon_webhook_not_configured", "message": "LEMON_SQUEEZY_WEBHOOK_SECRET is required."})

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid JSON payload."}) from exc

    event_id = _safe_nonempty(event.get("meta", {}).get("event_id") or event.get("data", {}).get("id"), 160)
    event_type = _safe_nonempty(event.get("meta", {}).get("event_name"), 120)
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Webhook event ID and event name are required."})

    obj = event.get("data", {}) or {}
    attrs = obj.get("attributes", {}) or {}
    custom = event.get("meta", {}).get("custom_data") or attrs.get("custom_data") or {}
    checkout_id = _safe_nonempty(custom.get("checkout_id"), 120)
    plan = str(custom.get("plan") or _plan_from_variant(attrs.get("variant_id")) or "single").lower()
    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook_plan", "message": "Webhook plan is not recognised."})
    email = _safe_nonempty(custom.get("email") or attrs.get("user_email") or attrs.get("customer_email"), 320)
    user_id = _safe_nonempty(custom.get("user_id") or custom.get("auth_user_id"), 80)
    project_id = _safe_nonempty(custom.get("project_id"), 120)
    if project_id == "none":
        project_id = None

    checkout_context = _checkout_owner_context(checkout_id)
    if checkout_context:
        checkout_plan = str(checkout_context.get("plan") or "").lower()
        if checkout_plan in PLAN_LIMITS and checkout_plan != plan:
            raise HTTPException(status_code=400, detail={"error": "checkout_plan_mismatch", "message": "Webhook plan does not match the server-created checkout."})
        plan = checkout_plan or plan
        email = checkout_context.get("owner_email") or email
        user_id = checkout_context.get("user_id") or user_id
        project_id = checkout_context.get("project_id") or project_id

    provider_event_id = f"lemon:{event_id}"
    summary = {
        "provider": "lemonsqueezy",
        "event_type": event_type,
        "resource_id": _safe_nonempty(obj.get("id"), 120),
        "checkout_id": checkout_id,
        "plan": plan,
        "owner_email_sha256": _email_fingerprint(email),
    }
    claim = _claim_payment_event(
        provider_event_id,
        event_type,
        summary,
        checkout_id=checkout_id,
        plan_name=plan,
        payload_sha256=_event_fingerprint(raw_body),
    )
    state = str(claim.get("state") or "").lower()
    if not claim.get("claimed"):
        if state == "dead_lettered":
            return {"status": "dead_lettered", "event_id": event_id, "event_type": event_type, "provider": "lemonsqueezy"}
        return {"status": "duplicate_ignored", "event_id": event_id, "event_type": event_type, "provider": "lemonsquee"}

    try:
        result = _process_lemon_event(
            event_type=event_type,
            event_id=provider_event_id,
            plan=plan,
            user_id=user_id,
            email=email,
            project_id=project_id,
            checkout_id=checkout_id,
            obj=obj,
            attrs=attrs,
        )
    except HTTPException:
        _complete_payment_event(provider_event_id, success=False, outcome={"status": "failed"}, error_code="http_error")
        raise
    except Exception as exc:
        _complete_payment_event(provider_event_id, success=False, outcome={"status": "failed"}, error_code=type(exc).__name__.lower()[:80])
        raise HTTPException(status_code=503, detail={"error": "payment_webhook_processing_failed", "message": "Payment event processing is temporarily unavailable; retry delivery."}) from exc

    _complete_payment_event(provider_event_id, success=True, outcome=result)
    return {"status": "handled", "event": event_type, "plan": plan, "provider": "lemonsqueezy", **result}


def _process_lemon_event(
    *,
    event_type: str,
    event_id: str,
    plan: str,
    user_id: Optional[str],
    email: Optional[str],
    project_id: Optional[str],
    checkout_id: Optional[str],
    obj: Dict[str, Any],
    attrs: Dict[str, Any],
) -> Dict[str, Any]:
    resource_id = _safe_nonempty(obj.get("id"), 120)
    provider_session_id = _safe_nonempty(attrs.get("checkout_id") or attrs.get("checkout"), 120)
    if event_type == "order_created":
        if plan == "single":
            credit = _grant_credit(
                user_id,
                email,
                project_id,
                source="lemon_one_time",
                event_id=event_id,
                checkout_id=checkout_id,
                provider_order_id=resource_id,
            )
            _mark_checkout_and_payment(checkout_id=checkout_id, provider_session_id=provider_session_id, status="paid", event_id=event_id, provider_order_id=resource_id)
            return {"outcome": "credit_granted", "checkout_id": checkout_id, "credit_id": (credit or {}).get("id")}
        _mark_checkout_and_payment(checkout_id=checkout_id, provider_session_id=provider_session_id, status="payment_pending", event_id=event_id, provider_order_id=resource_id)
        return {"outcome": "order_received", "checkout_id": checkout_id}
    if event_type in {"subscription_created", "subscription_updated", "subscription_resumed", "subscription_payment_success"}:
        subscription = _upsert_subscription(user_id, email, plan, _lemon_subscription_object(obj), status="active")
        _mark_checkout_and_payment(
            checkout_id=checkout_id,
            provider_session_id=provider_session_id,
            status="subscription_active",
            event_id=event_id,
            provider_order_id=resource_id if event_type == "subscription_payment_success" else None,
            provider_subscription_id=(subscription or {}).get("provider_subscription_id") or resource_id,
        )
        return {"outcome": "subscription_active", "checkout_id": checkout_id, "subscription_id": (subscription or {}).get("id")}
    if event_type in {"subscription_cancelled", "subscription_expired", "subscription_paused", "subscription_payment_failed"}:
        status = "past_due" if event_type == "subscription_payment_failed" else "canceled"
        subscription = _upsert_subscription(user_id, email, plan, _lemon_subscription_object(obj), status=status)
        checkout_status = "payment_failed" if event_type == "subscription_payment_failed" else "canceled"
        _mark_checkout_and_payment(checkout_id=checkout_id, provider_session_id=provider_session_id, status=checkout_status, event_id=event_id, provider_subscription_id=(subscription or {}).get("provider_subscription_id") or resource_id, failure_code=event_type)
        return {"outcome": status, "checkout_id": checkout_id, "subscription_id": (subscription or {}).get("id")}
    if event_type in {"order_refunded", "order_refund_created"}:
        revoked = _revoke_unspent_credit(checkout_id=checkout_id, provider_order_id=resource_id, event_id=event_id)
        return {"outcome": "refund_recorded", "checkout_id": checkout_id, **revoked}
    return {"outcome": "ignored", "checkout_id": checkout_id}


def _plan_from_variant(variant_id: Any) -> Optional[str]:
    if not variant_id:
        return None
    value = str(variant_id)
    for plan in PLAN_LIMITS:
        if value == str(os.getenv(_lemon_variant_env(plan)) or ""):
            return plan
    return None


def _lemon_subscription_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    attrs = obj.get("attributes", {}) or {}
    return {
        "id": str(obj.get("id") or ""),
        "customer": attrs.get("customer_id"),
        "subscription": str(obj.get("id") or ""),
        "attributes": attrs,
    }


def _lemon_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = os.getenv("LEMON_SQUEEZY_API_KEY")
    if not token:
        raise RuntimeError("LEMON_SQUEEZY_API_KEY is not configured.")
    req = urllib.request.Request(
        f"https://api.lemonsqueezy.com{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(raw) from exc


def _base_url() -> str:
    return os.getenv("PUBLIC_SITE_URL", "https://devbareun.com").rstrip("/")


def _append_checkout_id(url: str, checkout_id: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query["checkout_id"] = checkout_id
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def _safe_checkout_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail={"error": "invalid_url", "message": "Checkout redirect URL must use http/https."})
    allowed = [item.strip().rstrip("/") for item in os.getenv("DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS", "").split(",") if item.strip()]
    if not allowed:
        allowed = ["https://devbareun.com", "https://www.devbareun.com", "https://devbareun.vercel.app"]
        if not production_security_enabled():
            allowed.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"])
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin not in allowed:
        raise HTTPException(status_code=400, detail={"error": "invalid_url", "message": "Checkout redirect origin is not allowed."})
    return url
