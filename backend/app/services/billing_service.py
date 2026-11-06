from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
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


PAYMENTS_UNAVAILABLE_MESSAGE = "Online payment is not available yet. Email info@devbareun.com to activate this plan."

PAYMENT_PROVIDER = "polar"
PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT = 5
WEBHOOK_TOLERANCE_SECONDS = 5 * 60

# Polar checkout links created for the public pricing (USD): Single $29 one-time,
# Plus $49/month or $468/year, Pro $89/month or $852/year. Each link carries
# metadata {devbareun_plan, billing_cycle} and redirects to
# /workspace/?view=payment-success&plan=<plan>&checkout_id={CHECKOUT_ID}.
# Env vars override them (e.g. for a Polar sandbox organisation).
POLAR_CHECKOUT_LINKS = {
    ("single", "one_time"): ("POLAR_CHECKOUT_LINK_SINGLE", "https://buy.polar.sh/polar_cl_szYYkCz91NHY0MNcegmD63N0AHYN7EWxOP9Tr03afoc"),
    ("plus", "monthly"): ("POLAR_CHECKOUT_LINK_PLUS_MONTHLY", "https://buy.polar.sh/polar_cl_Gp9yMSwUpXn4oGWO7a4FqmS2mQIUowbsNUT4301fzA2"),
    ("plus", "annual"): ("POLAR_CHECKOUT_LINK_PLUS_ANNUAL", "https://buy.polar.sh/polar_cl_uA0hYBkyTQaVQrASOVNGtSE0Yb6Wb2XTMz3FJ07icfq"),
    ("pro", "monthly"): ("POLAR_CHECKOUT_LINK_PRO_MONTHLY", "https://buy.polar.sh/polar_cl_9pave0J8WhFANu9eKrsjCfSyxJRiFIuHuvfvo0qM1zi"),
    ("pro", "annual"): ("POLAR_CHECKOUT_LINK_PRO_ANNUAL", "https://buy.polar.sh/polar_cl_Nw75ouXSrrvIB6fNDZxevciQjNoHGnvKYb9wm3e7j3r"),
}


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


def create_subscription_checkout(user: CurrentUser, plan: str, success_url: Optional[str], cancel_url: Optional[str], billing_cycle: Optional[str] = None) -> Dict[str, Any]:
    plan = str(plan or "").lower()
    if plan not in {"plus", "pro"}:
        raise HTTPException(status_code=400, detail={"error": "invalid_plan", "message": "Subscription checkout supports Plus and Pro."})
    return _create_checkout(user=user, plan=plan, mode="subscription", success_url=success_url, cancel_url=cancel_url, billing_cycle=billing_cycle)


def create_one_time_checkout(user: CurrentUser, project_id: Optional[str], success_url: Optional[str], cancel_url: Optional[str]) -> Dict[str, Any]:
    return _create_checkout(user=user, plan="single", mode="payment", project_id=project_id, success_url=success_url, cancel_url=cancel_url)


def create_checkout_session(user: CurrentUser, plan: str, project_id: Optional[str], success_url: Optional[str], cancel_url: Optional[str], billing_cycle: Optional[str] = None) -> Dict[str, Any]:
    plan = str(plan or "single").lower()
    mode = "payment" if plan == "single" else "subscription"
    return _create_checkout(user=user, plan=plan, mode=mode, project_id=project_id, success_url=success_url, cancel_url=cancel_url, billing_cycle=billing_cycle)


def _create_checkout(
    *,
    user: CurrentUser,
    plan: str,
    mode: str,
    project_id: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    billing_cycle: Optional[str] = None,
) -> Dict[str, Any]:
    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail={"error": "invalid_plan", "message": f"Unsupported plan: {plan}"})
    cycle = _normalize_cycle(plan, billing_cycle)
    if not _payments_enabled():
        if not production_security_enabled() and bool_env("DEVBAREUN_ENABLE_MOCK_PAYMENT", False):
            return {"mode": "mock_disabled_by_default", "checkout_url": None, "plan": plan}
        raise HTTPException(status_code=503, detail={"error": "payments_unavailable", "message": PAYMENTS_UNAVAILABLE_MESSAGE})
    link = _checkout_link(plan, cycle)
    if not link:
        raise HTTPException(status_code=503, detail={"error": "payments_unavailable", "message": PAYMENTS_UNAVAILABLE_MESSAGE})

    checkout_id = str(uuid4())
    query = {"reference_id": checkout_id}
    if user.email and "@" in user.email:
        query["customer_email"] = user.email
    checkout_url = f"{link}?{urllib.parse.urlencode(query)}"
    _record_checkout_session(user, checkout_id=checkout_id, plan=plan, project_id=project_id, checkout_url=checkout_url)
    _insert_payment(user, plan, project_id, checkout_id)
    return {
        "checkout_url": checkout_url,
        "checkout_id": checkout_id,
        "mode": mode,
        "plan": plan,
        "billing_cycle": cycle,
        "provider": PAYMENT_PROVIDER,
    }


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
        # The Polar success URL carries Polar's checkout ID. It is linked to our
        # record when the order webhook arrives, so keep the page polling until then.
        checkout = select_one("checkout_sessions", {"provider_checkout_session_id": normalized})
    if not checkout:
        return {
            "checkout": {"checkout_id": normalized, "plan_code": None, "status": "payment_pending"},
            "payment": None,
            "poll_after_seconds": 5,
        }
    if not can_access_project_scope(user.role, "payments") and str(checkout.get("owner_email") or "").lower() != str(user.email or "").lower():
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Checkout belongs to another customer."})
    payment = select_one("payments", {"checkout_id": checkout.get("checkout_id")})
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



# ---------------------------------------------------------------------------
# Polar (polar.sh) checkout links and signed webhooks
# ---------------------------------------------------------------------------


def _payments_enabled() -> bool:
    """Online checkout opens only when the webhook can credit the purchase."""
    if not bool_env("DEVBAREUN_PAYMENTS_ENABLED", True):
        return False
    return bool(os.getenv("POLAR_WEBHOOK_SECRET", "").strip())


def _normalize_cycle(plan: str, billing_cycle: Optional[str]) -> str:
    if plan == "single":
        return "one_time"
    value = str(billing_cycle or "monthly").strip().lower()
    if value in {"annual", "annually", "year", "yearly"}:
        return "annual"
    return "monthly"


def _checkout_link(plan: str, cycle: str) -> Optional[str]:
    entry = POLAR_CHECKOUT_LINKS.get((plan, cycle))
    if not entry:
        return None
    env_name, default = entry
    url = os.getenv(env_name, "").strip() or default
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return url


def _event_max_attempts() -> int:
    try:
        return max(1, min(20, int(os.getenv("PAYMENT_EVENT_MAX_ATTEMPTS", PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT))))
    except (TypeError, ValueError):
        return PAYMENT_EVENT_MAX_ATTEMPTS_DEFAULT


def _event_fingerprint(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _email_fingerprint(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _user_uuid(user: CurrentUser) -> Optional[str]:
    if uuid_like(user.id):
        return user.id
    if uuid_like(user.auth_user_id):
        return user.auth_user_id
    return None


def _record_checkout_session(user: CurrentUser, *, checkout_id: str, plan: str, project_id: Optional[str], checkout_url: str) -> None:
    if not is_configured():
        return
    payload = {
        "checkout_id": checkout_id,
        "plan_code": plan,
        "project_id": _safe_nonempty(project_id, 120),
        "user_id": _user_uuid(user),
        "owner_email": user.email,
        "customer_email": user.email,
        "provider_checkout_session_id": None,
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


def _insert_payment(user: CurrentUser, plan: str, project_id: Optional[str], checkout_id: str) -> None:
    if not is_configured():
        return
    payload = {
        "user_id": _user_uuid(user),
        "owner_email": user.email,
        "project_id": project_id if uuid_like(str(project_id or "")) else None,
        "provider": PAYMENT_PROVIDER,
        "payment_provider": PAYMENT_PROVIDER,
        "checkout_id": checkout_id,
        "plan_name": plan,
        "plan_code": plan,
        "amount": None,
        "currency": "usd",
        "status": "checkout_created",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    try:
        insert_row("payments", payload)
    except ProductionStoreError as exc:
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "checkout_payment_record_unavailable", "message": "Checkout payment record could not be created."}) from exc


def verify_polar_signature(raw_body: bytes, headers: Dict[str, Optional[str]], secret: str, *, now: Optional[float] = None) -> None:
    """Verify a Standard Webhooks signature as sent by Polar.

    Polar signs ``{webhook-id}.{webhook-timestamp}.{body}`` with HMAC-SHA256 and
    sends ``webhook-signature: v1,<base64>`` (space separated when rotated).
    Secrets created since 2026-09-08 are Standard Webhooks keys
    (``whsec_<base64 key>``); older Polar secrets are keyed with the UTF-8
    bytes of the whole secret. Both derivations are accepted.
    """
    msg_id = str(headers.get("webhook-id") or "").strip()
    timestamp = str(headers.get("webhook-timestamp") or "").strip()
    signature_header = str(headers.get("webhook-signature") or "").strip()
    if not msg_id or not timestamp or not signature_header:
        raise HTTPException(status_code=400, detail={"error": "missing_signature", "message": "Missing webhook signature headers."})
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid webhook timestamp."}) from exc
    current = time.time() if now is None else now
    if abs(current - sent_at) > WEBHOOK_TOLERANCE_SECONDS:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Webhook timestamp is outside the allowed window."})
    signed = f"{msg_id}.{timestamp}.".encode("utf-8") + raw_body
    expected = [base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode("ascii") for key in _webhook_keys(secret)]
    for candidate in signature_header.split():
        version, _, value = candidate.partition(",")
        if version == "v1" and value and any(hmac.compare_digest(value, item) for item in expected):
            return
    raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid Polar webhook signature."})


def _webhook_keys(secret: str) -> List[bytes]:
    keys: List[bytes] = []
    if secret.startswith("whsec_"):
        try:
            keys.append(base64.b64decode(secret[len("whsec_"):], validate=True))
        except (ValueError, TypeError):
            pass
    keys.append(secret.encode("utf-8"))
    return keys


def handle_webhook(raw_body: bytes, headers: Dict[str, Optional[str]]) -> Dict[str, Any]:
    secret = os.getenv("POLAR_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail={"error": "polar_webhook_not_configured", "message": "POLAR_WEBHOOK_SECRET is required."})
    verify_polar_signature(raw_body, headers, secret)

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid JSON payload."}) from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Invalid webhook payload."})

    event_type = _safe_nonempty(event.get("type"), 120)
    obj = event.get("data") if isinstance(event.get("data"), dict) else {}
    webhook_id = _safe_nonempty(headers.get("webhook-id"), 160)
    if not event_type or not webhook_id:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Webhook event ID and type are required."})

    if event_type not in POLAR_HANDLED_EVENTS:
        return {"status": "ignored", "event": event_type, "provider": PAYMENT_PROVIDER}

    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    product = obj.get("product") if isinstance(obj.get("product"), dict) else {}
    product_meta = product.get("metadata") if isinstance(product.get("metadata"), dict) else {}
    customer = obj.get("customer") if isinstance(obj.get("customer"), dict) else {}

    checkout_id = _safe_nonempty(metadata.get("reference_id"), 120)
    polar_checkout_id = _safe_nonempty(obj.get("checkout_id"), 120)
    plan = str(metadata.get("devbareun_plan") or product_meta.get("devbareun_plan") or "").strip().lower()
    cycle = str(metadata.get("billing_cycle") or product_meta.get("billing_cycle") or "").strip().lower()
    if plan not in PLAN_LIMITS:
        # Not a DevBareun plan product (e.g. created manually in Polar).
        return {"status": "ignored", "event": event_type, "reason": "unknown_product", "provider": PAYMENT_PROVIDER}
    email = _safe_nonempty(customer.get("email"), 320)
    user_id: Optional[str] = None
    project_id: Optional[str] = None

    checkout_context = _checkout_owner_context(checkout_id)
    if checkout_context:
        checkout_plan = str(checkout_context.get("plan") or "").lower()
        if checkout_plan in PLAN_LIMITS and checkout_plan != plan:
            raise HTTPException(status_code=400, detail={"error": "checkout_plan_mismatch", "message": "Webhook plan does not match the server-created checkout."})
        email = checkout_context.get("owner_email") or email
        user_id = checkout_context.get("user_id")
        project_id = checkout_context.get("project_id")
    email = (email or "").strip().lower() or None
    if not email:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Webhook has no customer email."})

    provider_event_id = f"polar:{webhook_id}"
    summary = {
        "provider": PAYMENT_PROVIDER,
        "event_type": event_type,
        "resource_id": _safe_nonempty(obj.get("id"), 120),
        "checkout_id": checkout_id,
        "polar_checkout_id": polar_checkout_id,
        "plan": plan,
        "billing_cycle": cycle or None,
        "owner_email_sha256": _email_fingerprint(email),
    }
    claim = _claim_payment_event(provider_event_id, event_type, summary, checkout_id=checkout_id, plan_name=plan, payload_sha256=_event_fingerprint(raw_body))
    if not claim.get("claimed"):
        state = str(claim.get("state") or "").lower()
        status = "dead_lettered" if state == "dead_lettered" else "duplicate_ignored"
        return {"status": status, "event": event_type, "provider": PAYMENT_PROVIDER}

    try:
        result = _process_polar_event(
            event_type=event_type,
            event_id=provider_event_id,
            plan=plan,
            cycle=cycle,
            user_id=user_id,
            email=email,
            project_id=project_id,
            checkout_id=checkout_id,
            polar_checkout_id=polar_checkout_id,
            obj=obj,
        )
    except HTTPException:
        _complete_payment_event(provider_event_id, success=False, outcome={"status": "failed"}, error_code="http_error")
        raise
    except Exception as exc:
        _complete_payment_event(provider_event_id, success=False, outcome={"status": "failed"}, error_code=type(exc).__name__.lower()[:80])
        raise HTTPException(status_code=503, detail={"error": "payment_webhook_processing_failed", "message": "Payment event processing is temporarily unavailable; retry delivery."}) from exc

    _complete_payment_event(provider_event_id, success=True, outcome=result)
    return {"status": "handled", "event": event_type, "plan": plan, "provider": PAYMENT_PROVIDER, **result}


POLAR_HANDLED_EVENTS = {
    "order.paid",
    "order.refunded",
    "subscription.created",
    "subscription.active",
    "subscription.updated",
    "subscription.canceled",
    "subscription.uncanceled",
    "subscription.revoked",
    "subscription.past_due",
}


def _process_polar_event(
    *,
    event_type: str,
    event_id: str,
    plan: str,
    cycle: str,
    user_id: Optional[str],
    email: str,
    project_id: Optional[str],
    checkout_id: Optional[str],
    polar_checkout_id: Optional[str],
    obj: Dict[str, Any],
) -> Dict[str, Any]:
    resource_id = _safe_nonempty(obj.get("id"), 120)
    if event_type == "order.paid":
        if plan == "single":
            credit = _grant_credit(user_id, email, project_id, event_id=event_id, checkout_id=checkout_id, provider_order_id=resource_id)
            _mark_checkout_and_payment(checkout_id=checkout_id, polar_checkout_id=polar_checkout_id, status="paid", event_id=event_id, provider_order_id=resource_id, amount=obj.get("total_amount"), currency=obj.get("currency"))
            return {"outcome": "credit_granted", "checkout_id": checkout_id, "credit_id": (credit or {}).get("id")}
        subscription_obj = obj.get("subscription") if isinstance(obj.get("subscription"), dict) else {}
        subscription = None
        if subscription_obj:
            subscription = _upsert_subscription(user_id, email, plan, cycle, subscription_obj, status="active")
        _mark_checkout_and_payment(
            checkout_id=checkout_id,
            polar_checkout_id=polar_checkout_id,
            status="subscription_active",
            event_id=event_id,
            provider_order_id=resource_id,
            provider_subscription_id=_safe_nonempty(obj.get("subscription_id"), 120),
            amount=obj.get("total_amount"),
            currency=obj.get("currency"),
        )
        return {"outcome": "subscription_paid", "checkout_id": checkout_id, "subscription_id": (subscription or {}).get("id")}
    if event_type.startswith("subscription."):
        status = _subscription_status(obj, event_type)
        subscription = _upsert_subscription(user_id, email, plan, cycle, obj, status=status)
        if status == "active":
            _mark_checkout_and_payment(checkout_id=checkout_id, polar_checkout_id=polar_checkout_id, status="subscription_active", event_id=event_id, provider_subscription_id=resource_id)
        elif event_type in {"subscription.revoked", "subscription.past_due"}:
            _mark_checkout_and_payment(
                checkout_id=checkout_id,
                polar_checkout_id=polar_checkout_id,
                status="payment_failed" if status == "past_due" else "canceled",
                event_id=event_id,
                provider_subscription_id=resource_id,
                failure_code=event_type,
            )
        return {"outcome": f"subscription_{status}", "checkout_id": checkout_id, "subscription_id": (subscription or {}).get("id")}
    if event_type == "order.refunded":
        if plan != "single":
            return {"outcome": "subscription_refund_recorded", "checkout_id": checkout_id}
        revoked = _revoke_unspent_credit(checkout_id=checkout_id, provider_order_id=resource_id, event_id=event_id)
        return {"outcome": "refund_recorded", "checkout_id": checkout_id, **revoked}
    return {"outcome": "ignored", "checkout_id": checkout_id}


def _subscription_status(obj: Dict[str, Any], event_type: str) -> str:
    """Map Polar's subscription state to DevBareun access.

    A cancellation scheduled for the period end keeps access until then
    (Polar reports status=active with cancel_at_period_end=true).
    """
    if event_type == "subscription.revoked":
        return "canceled"
    raw = str(obj.get("status") or "").lower()
    if raw in {"active", "trialing"}:
        return "active"
    if raw in {"past_due", "unpaid"}:
        return "past_due"
    if raw in {"incomplete"}:
        return "incomplete"
    return "canceled"


def _checkout_owner_context(checkout_id: Optional[str]) -> Dict[str, Any]:
    """Resolve the owner from the server-created checkout, not from webhook data."""
    if not checkout_id or not is_configured():
        return {}
    try:
        checkout = select_one("checkout_sessions", {"checkout_id": checkout_id})
    except ProductionStoreError:
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "checkout_lookup_unavailable", "message": "Checkout ownership could not be verified."})
        return {}
    if not checkout:
        return {}
    return {
        "owner_email": _safe_nonempty(checkout.get("owner_email") or checkout.get("customer_email"), 320),
        "user_id": _safe_nonempty(checkout.get("user_id"), 80),
        "project_id": _safe_nonempty(checkout.get("project_id"), 120),
        "plan": _safe_nonempty(checkout.get("plan_code"), 32),
    }


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
                "p_provider": PAYMENT_PROVIDER,
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


def _mark_checkout_and_payment(
    *,
    checkout_id: Optional[str],
    polar_checkout_id: Optional[str],
    status: str,
    event_id: str,
    provider_order_id: Optional[str] = None,
    provider_subscription_id: Optional[str] = None,
    failure_code: Optional[str] = None,
    amount: Any = None,
    currency: Any = None,
) -> None:
    if not is_configured() or not (checkout_id or polar_checkout_id):
        return
    now = _now_iso()
    paid = status in {"paid", "subscription_active"}
    checkout_patch: Dict[str, Any] = {"status": status, "last_event_id": event_id, "failure_code": failure_code, "updated_at": now}
    payment_patch: Dict[str, Any] = {"status": status, "last_provider_event_id": event_id, "failure_reason_code": failure_code, "updated_at": now}
    if paid:
        checkout_patch["paid_at"] = now
        payment_patch["paid_at"] = now
    if polar_checkout_id:
        checkout_patch["provider_checkout_session_id"] = polar_checkout_id
        payment_patch["provider_checkout_session_id"] = polar_checkout_id
        payment_patch["provider_session_id"] = polar_checkout_id
    if provider_order_id:
        checkout_patch["provider_order_id"] = provider_order_id
        payment_patch["provider_order_id"] = provider_order_id
    if provider_subscription_id:
        payment_patch["provider_subscription_id"] = provider_subscription_id
    if isinstance(amount, int):
        payment_patch["amount"] = round(amount / 100, 2)
    if currency:
        payment_patch["currency"] = str(currency).lower()[:8]
    filters = {"checkout_id": checkout_id} if checkout_id else {"provider_checkout_session_id": polar_checkout_id}
    for table, patch in (("checkout_sessions", checkout_patch), ("payments", payment_patch)):
        try:
            first_update(table, filters, patch)
        except ProductionStoreError:
            continue


def _subscription_period(obj: Dict[str, Any], existing: Optional[Dict[str, Any]], cycle: str) -> tuple[datetime, datetime]:
    days = 365 if cycle == "annual" else 30
    start = _parse_timestamp(obj.get("current_period_start"))
    end = _parse_timestamp(obj.get("current_period_end") or obj.get("ends_at"))
    if end and not start:
        start = end - timedelta(days=days)
    if not end:
        prior_end = _parse_timestamp((existing or {}).get("current_period_end"))
        if prior_end and prior_end > _now():
            return _parse_timestamp((existing or {}).get("current_period_start")) or (prior_end - timedelta(days=days)), prior_end
        start = start or _now()
        end = start + timedelta(days=days)
    return start or (end - timedelta(days=days)), end


def _period_limit(plan: str, cycle: str) -> int:
    monthly = int(PLAN_LIMITS[plan]["limit"])
    # Annual plans keep the advertised monthly allowance for the whole year.
    return monthly * 12 if cycle == "annual" else monthly


def _upsert_subscription(user_id: Optional[str], email: str, plan: str, cycle: str, obj: Dict[str, Any], status: str) -> Dict[str, Any] | None:
    if not is_configured():
        return None
    provider_subscription_id = _safe_nonempty(obj.get("id"), 120)
    if not provider_subscription_id:
        return None
    if cycle not in {"monthly", "annual"}:
        cycle = "annual" if str(obj.get("recurring_interval") or "").lower() == "year" else "monthly"
    existing = select_one("subscriptions", {"provider_subscription_id": provider_subscription_id})
    period_start, period_end = _subscription_period(obj, existing, cycle)
    prior_end = _parse_timestamp((existing or {}).get("current_period_end"))
    # Usage resets only when the provider billing period actually advances.
    usage = int((existing or {}).get("used_project_count") or 0)
    if prior_end and period_end > prior_end:
        usage = 0
    payload = {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "plan_name": plan,
        "plan_code": plan,
        "status": status,
        "monthly_project_limit": _period_limit(plan, cycle),
        "used_project_count": usage,
        "current_period_start": period_start.isoformat(),
        "current_period_end": period_end.isoformat(),
        "provider": PAYMENT_PROVIDER,
        "provider_customer_id": _safe_nonempty(obj.get("customer_id"), 120),
        "provider_subscription_id": provider_subscription_id,
        "updated_at": _now_iso(),
    }
    if existing:
        if not payload["user_id"]:
            payload.pop("user_id")
        return first_update("subscriptions", {"id": existing["id"]}, payload) or existing
    payload["created_at"] = _now_iso()
    return insert_row("subscriptions", payload)


def _grant_credit(
    user_id: Optional[str],
    email: str,
    project_id: Optional[str],
    *,
    event_id: str,
    checkout_id: Optional[str],
    provider_order_id: Optional[str],
) -> Dict[str, Any] | None:
    if not is_configured():
        return None
    if provider_order_id:
        existing = select_one("analysis_credits", {"provider_order_id": provider_order_id})
        if existing:
            return existing
    existing = select_one("analysis_credits", {"source_event_id": event_id})
    if existing:
        return existing
    return insert_row("analysis_credits", {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "project_id": project_id if uuid_like(str(project_id or "")) else None,
        "source": "polar_one_time",
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
    })


def _revoke_unspent_credit(*, checkout_id: Optional[str], provider_order_id: Optional[str], event_id: str) -> Dict[str, Any]:
    if not is_configured():
        return {"revoked": False, "reason": "local"}
    credit = select_one("analysis_credits", {"provider_order_id": provider_order_id}) if provider_order_id else None
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
    _mark_checkout_and_payment(checkout_id=checkout_id, polar_checkout_id=None, status="refunded", event_id=event_id, provider_order_id=provider_order_id)
    return {"revoked": True, "credit_id": credit.get("id")}
