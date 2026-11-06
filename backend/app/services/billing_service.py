from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


PAYMENTS_UNAVAILABLE_MESSAGE = "Online payment is not available yet. Email info@devbareun.com to activate this plan."


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
    if not production_security_enabled() and bool_env("DEVBAREUN_ENABLE_MOCK_PAYMENT", False):
        return {"mode": "mock_disabled_by_default", "checkout_url": None, "plan": plan}
    # No online payment provider is connected. Plans are activated manually.
    raise HTTPException(status_code=503, detail={"error": "payments_unavailable", "message": PAYMENTS_UNAVAILABLE_MESSAGE})


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

