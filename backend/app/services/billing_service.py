from __future__ import annotations

import json
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..auth_dependencies import CurrentUser, local_store_enabled
from ..production_store import ProductionStoreError, first_update, insert_row, is_configured, select_one, select_rows, uuid_like
from ..security_runtime import bool_env, production_security_enabled


PLAN_LIMITS = {
    "single": {"limit": 1, "kind": "one_time"},
    "plus": {"limit": 5, "kind": "subscription"},
    "pro": {"limit": 20, "kind": "subscription"},
}


def get_billing_status(user: CurrentUser) -> Dict[str, Any]:
    if user.is_admin:
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
    if user.is_admin:
        return {"consumed": False, "mode": "admin_unlimited"}
    subscriptions = _active_subscriptions(user)
    if subscriptions:
        sub = subscriptions[0]
        limit = int(sub.get("monthly_project_limit") or PLAN_LIMITS.get(str(sub.get("plan_name") or "").lower(), {}).get("limit") or 0)
        used = int(sub.get("used_project_count") or 0)
        if limit and used < limit:
            patch = {"used_project_count": used + 1, "updated_at": datetime.utcnow().isoformat()}
            updated = _update_by_id("subscriptions", sub, patch)
            _log_activity(user, project_id, "billing.subscription_usage_consumed", {"job_id": job_id, "subscription_id": sub.get("id")})
            return {"consumed": True, "mode": "subscription", "subscription": updated or sub}
    for credit in _active_credits(user):
        remaining = int(credit.get("remaining") or credit.get("remaining_credits") or 0)
        if remaining > 0:
            amount = int(credit.get("amount") or credit.get("total_credits") or remaining)
            patch = {"remaining": remaining - 1} if is_configured() else {"remaining": remaining - 1, "remaining_credits": remaining - 1}
            updated = _update_by_id("analysis_credits", credit, patch)
            _log_activity(user, project_id, "billing.credit_consumed", {"job_id": job_id, "credit_id": credit.get("id"), "amount": amount})
            return {"consumed": True, "mode": "credit", "credit": updated or credit}
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

            return [row for row in list_rows("subscriptions", owner_email=user.email) if str(row.get("status")).lower() == "active"]
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Supabase PostgreSQL is required for billing status."})
        return []
    rows = select_rows("subscriptions", {"owner_email": user.email}, limit=100)
    active = [row for row in rows if str(row.get("status") or "").lower() in {"active", "trialing"}]
    active.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
    return active


def _active_credits(user: CurrentUser) -> List[Dict[str, Any]]:
    if not is_configured():
        if local_store_enabled():
            from ..saas_store import list_rows

            rows = list_rows("analysis_credits", owner_email=user.email)
            return [row for row in rows if str(row.get("status") or "active").lower() == "active"]
        return []
    rows = select_rows("analysis_credits", {"owner_email": user.email}, limit=200)
    return [row for row in rows if int(row.get("remaining") or row.get("remaining_credits") or 0) > 0]


def _update_by_id(table: str, row: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any] | None:
    row_id = row.get("id")
    if is_configured() and row_id:
        return first_update(table, {"id": row_id}, patch)
    if local_store_enabled():
        from ..saas_store import update_one

        key = "id" if row.get("id") else f"{table[:-1]}_id"
        return update_one(table, key, row.get(key), patch)
    return None


def _insert_payment(user: CurrentUser, plan: str, session: Dict[str, Any], project_id: Optional[str]) -> None:
    payload = {
        "user_id": user.id if uuid_like(user.id) else (user.auth_user_id if uuid_like(user.auth_user_id) else None),
        "owner_email": user.email,
        "project_id": project_id if uuid_like(str(project_id or "")) else None,
        "provider": "lemonsqueezy",
        "provider_session_id": session.get("id"),
        "plan_name": plan,
        "amount": None,
        "currency": os.getenv("LEMON_SQUEEZY_CURRENCY", "usd"),
        "status": "checkout_created",
        "created_at": datetime.utcnow().isoformat(),
    }
    if is_configured():
        try:
            insert_row("payments", payload)
        except ProductionStoreError:
            return


def _payment_event_seen(event_id: str) -> bool:
    if not is_configured():
        return False
    return bool(select_one("payment_events", {"provider_event_id": event_id}))


def _record_payment_event(event_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    if not is_configured():
        return
    insert_row("payment_events", {"provider_event_id": event_id, "event_type": event_type, "payload": payload, "processed_at": datetime.utcnow().isoformat()})


def _upsert_subscription(user_id: Optional[str], email: Optional[str], plan: str, obj: Dict[str, Any], status: str) -> None:
    if not is_configured():
        return
    existing = select_one("subscriptions", {"provider_subscription_id": obj.get("subscription") or obj.get("id")}) if (obj.get("subscription") or obj.get("id")) else None
    period_start = datetime.utcnow()
    period_end = period_start + timedelta(days=30)
    payload = {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "plan_name": plan,
        "status": status,
        "monthly_project_limit": PLAN_LIMITS[plan]["limit"],
        "used_project_count": int((existing or {}).get("used_project_count") or 0),
        "current_period_start": period_start.isoformat(),
        "current_period_end": period_end.isoformat(),
        "provider": "lemonsqueezy",
        "provider_customer_id": obj.get("customer"),
        "provider_subscription_id": obj.get("subscription") or obj.get("id"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if existing:
        first_update("subscriptions", {"id": existing["id"]}, payload)
    else:
        payload["created_at"] = datetime.utcnow().isoformat()
        insert_row("subscriptions", payload)


def _grant_credit(user_id: Optional[str], email: Optional[str], project_id: Optional[str], source: str, provider_session_id: Optional[str]) -> None:
    if not is_configured():
        return
    existing = select_one("payments", {"provider_session_id": provider_session_id}) if provider_session_id else None
    if existing and str(existing.get("status")) == "paid_credit_granted":
        return
    insert_row("analysis_credits", {
        "user_id": user_id if uuid_like(str(user_id or "")) else None,
        "owner_email": email,
        "source": source,
        "credit_type": "single_project",
        "amount": 1,
        "remaining": 1,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat(),
    })
    if existing and existing.get("id"):
        first_update("payments", {"id": existing["id"]}, {"status": "paid_credit_granted"})


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
            "created_at": datetime.utcnow().isoformat(),
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

    success = _safe_checkout_url(success_url or f"{_base_url()}/billing.html?checkout=success&provider=lemonsqueezy")
    metadata = {
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
    _insert_payment(user, plan, session, project_id)
    return {"checkout_url": attrs.get("url"), "session_id": session["id"], "mode": mode, "plan": plan, "provider": "lemonsqueezy"}


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

    event_id = str(event.get("meta", {}).get("event_id") or event.get("data", {}).get("id") or "")
    event_type = str(event.get("meta", {}).get("event_name") or "")
    if not event_type:
        raise HTTPException(status_code=400, detail={"error": "invalid_webhook", "message": "Webhook event name is missing."})
    if event_id and _payment_event_seen(f"lemon:{event_id}"):
        return {"status": "duplicate_ignored", "event_id": event_id, "event_type": event_type, "provider": "lemonsqueezy"}
    if event_id:
        _record_payment_event(f"lemon:{event_id}", event_type, event)

    obj = event.get("data", {}) or {}
    attrs = obj.get("attributes", {}) or {}
    custom = event.get("meta", {}).get("custom_data") or attrs.get("custom_data") or {}
    plan = str(custom.get("plan") or _plan_from_variant(attrs.get("variant_id")) or "single").lower()
    email = custom.get("email") or attrs.get("user_email") or attrs.get("customer_email")
    user_id = custom.get("user_id") or custom.get("auth_user_id")
    project_id = custom.get("project_id") or None

    if event_type == "order_created":
        if plan == "single":
            _grant_credit(user_id, email, project_id, source="lemon_one_time", provider_session_id=str(obj.get("id") or ""))
        return {"status": "handled", "event": event_type, "plan": plan, "provider": "lemonsqueezy"}
    if event_type in {"subscription_created", "subscription_updated", "subscription_resumed", "subscription_payment_success"}:
        _upsert_subscription(user_id, email, plan if plan in {"plus", "pro"} else "plus", _lemon_subscription_object(obj), status="active")
        return {"status": "handled", "event": event_type, "plan": plan, "provider": "lemonsqueezy"}
    if event_type in {"subscription_cancelled", "subscription_expired", "subscription_paused", "subscription_payment_failed"}:
        status = "past_due" if event_type == "subscription_payment_failed" else "canceled"
        _upsert_subscription(user_id, email, plan if plan in {"plus", "pro"} else "plus", _lemon_subscription_object(obj), status=status)
        return {"status": "handled", "event": event_type, "plan": plan, "provider": "lemonsqueezy"}
    return {"status": "ignored", "event": event_type, "provider": "lemonsqueezy"}


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
