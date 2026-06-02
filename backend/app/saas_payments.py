from __future__ import annotations

import os
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import stripe
except Exception:  # pragma: no cover - optional until Stripe is configured
    stripe = None

from .saas_ids import make_public_id
from .saas_store import insert, find_one, list_rows, update_one, log_activity
from .security_runtime import production_security_enabled, stripe_webhook_must_verify

BASE_DIR = Path(__file__).resolve().parent.parent
LEGACY_PROJECT_DIR = BASE_DIR / "data" / "projects"

PLAN_CONFIG: Dict[str, Dict[str, Any]] = {
    "single": {
        "label": "Single Project",
        "kind": "one_time",
        "credits": 1,
        "default_amount_cents": int(os.getenv("STRIPE_SINGLE_PROJECT_AMOUNT_CENTS", "2900")),
        "price_env": "STRIPE_SINGLE_PROJECT_PRICE_ID",
    },
    "plus": {
        "label": "Plus",
        "kind": "subscription",
        "credits": 5,
        "price_env": "STRIPE_PLUS_PRICE_ID",
    },
    "pro": {
        "label": "Pro",
        "kind": "subscription",
        "credits": 20,
        "price_env": "STRIPE_PRO_PRICE_ID",
    },
}


def _stripe_ready() -> bool:
    secret = os.getenv("STRIPE_SECRET_KEY")
    if secret and stripe is not None:
        stripe.api_key = secret
        return True
    return False


def _base_url() -> str:
    return os.getenv("PUBLIC_SITE_URL", "https://devbareun.com").rstrip("/")


def _safe_checkout_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Checkout redirect URL must use http/https.")
    allowed = [item.strip().rstrip("/") for item in os.getenv("DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS", "").split(",") if item.strip()]
    if not allowed:
        allowed = [
            "https://devbareun.com",
            "https://www.devbareun.com",
            "https://devbareun.vercel.app",
        ]
        if not production_security_enabled():
            allowed.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ])
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin not in allowed:
        raise ValueError("Checkout redirect origin is not allowed.")
    return url


def create_checkout_session(
    *,
    plan_code: str,
    customer_email: Optional[str] = None,
    project_id: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Stripe checkout session when configured; otherwise create a reviewable pilot checkout record."""
    if plan_code not in PLAN_CONFIG:
        raise ValueError(f"Unsupported plan code: {plan_code}")

    plan = PLAN_CONFIG[plan_code]
    checkout_id = make_public_id("checkout")
    success = _safe_checkout_url(success_url or f"{_base_url()}/payment-success?checkout_id={checkout_id}")
    cancel = _safe_checkout_url(cancel_url or f"{_base_url()}/payment-failed?checkout_id={checkout_id}")

    row = insert("checkout_sessions", {
        "checkout_id": checkout_id,
        "plan_code": plan_code,
        "plan_label": plan["label"],
        "kind": plan["kind"],
        "project_id": project_id,
        "customer_email": customer_email,
        "status": "created",
        "provider": "stripe",
        "success_url": success,
        "cancel_url": cancel,
    })

    if not _stripe_ready():
        update_one("checkout_sessions", "checkout_id", checkout_id, {
            "status": "created_without_stripe_secret",
            "mode": "pilot",
            "checkout_url": None,
        })
        log_activity(customer_email, "payment.checkout_created_pilot", {"checkout_id": checkout_id, "plan_code": plan_code})
        return {"checkout_session": find_one("checkout_sessions", checkout_id=checkout_id), "checkout_url": None, "mode": "stripe_secret_missing"}

    price_id = os.getenv(plan["price_env"])
    metadata = {"checkout_id": checkout_id, "plan_code": plan_code, "project_id": project_id or ""}
    mode = "payment" if plan["kind"] == "one_time" else "subscription"

    kwargs: Dict[str, Any] = {
        "mode": mode,
        "success_url": success,
        "cancel_url": cancel,
        "customer_email": customer_email,
        "metadata": metadata,
    }

    if price_id:
        kwargs["line_items"] = [{"price": price_id, "quantity": 1}]
    elif plan_code == "single":
        kwargs["line_items"] = [{
            "price_data": {
                "currency": os.getenv("STRIPE_CURRENCY", "usd"),
                "unit_amount": int(plan["default_amount_cents"]),
                "product_data": {"name": "DevBareun Single Project Review"},
            },
            "quantity": 1,
        }]
    else:
        raise RuntimeError(f"Missing Stripe price id environment variable: {plan['price_env']}")

    session = stripe.checkout.Session.create(**kwargs)
    update_one("checkout_sessions", "checkout_id", checkout_id, {
        "status": "stripe_session_created",
        "stripe_session_id": session.id,
        "checkout_url": session.url,
    })
    log_activity(customer_email, "payment.checkout_created", {"checkout_id": checkout_id, "stripe_session_id": session.id, "plan_code": plan_code})
    return {"checkout_session": find_one("checkout_sessions", checkout_id=checkout_id), "checkout_url": session.url, "mode": mode}


def _grant_credits(owner_email: str, plan_code: str, source: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    plan = PLAN_CONFIG[plan_code]
    total = int(plan["credits"])
    credit = insert("analysis_credits", {
        "credit_id": make_public_id("credit"),
        "source": source,
        "plan_code": plan_code,
        "owner_email": owner_email,
        "project_id": project_id,
        "total_credits": total,
        "used_credits": 0,
        "remaining_credits": total,
        "status": "active",
        "period_start": datetime.utcnow().date().isoformat(),
        "period_end": None,
    })
    return credit


def activate_checkout(checkout_id: str, stripe_session_id: Optional[str] = None, customer_email: Optional[str] = None) -> Dict[str, Any]:
    session = find_one("checkout_sessions", checkout_id=checkout_id)
    if not session:
        raise ValueError("Checkout session not found")
    plan_code = session.get("plan_code")
    owner_email = customer_email or session.get("customer_email")
    if not owner_email:
        owner_email = f"guest-{checkout_id.lower()}@devbareun.local"

    payment = insert("payments", {
        "payment_id": make_public_id("payment"),
        "checkout_id": checkout_id,
        "stripe_session_id": stripe_session_id or session.get("stripe_session_id"),
        "owner_email": owner_email,
        "project_id": session.get("project_id"),
        "plan_code": plan_code,
        "status": "paid",
        "paid_at": datetime.utcnow().isoformat(),
    })
    update_one("checkout_sessions", "checkout_id", checkout_id, {"status": "paid", "paid_at": datetime.utcnow().isoformat()})

    if plan_code in {"plus", "pro"}:
        subscription = insert("subscriptions", {
            "subscription_id": make_public_id("subscription"),
            "owner_email": owner_email,
            "plan_code": plan_code,
            "status": "active",
            "stripe_subscription_id": None,
            "monthly_credits": PLAN_CONFIG[plan_code]["credits"],
        })
        credit = _grant_credits(owner_email, plan_code, "subscription", session.get("project_id"))
        return {"payment": payment, "subscription": subscription, "credit": credit}

    credit = _grant_credits(owner_email, "single", "single_project", session.get("project_id"))
    if session.get("project_id"):
        update_one("projects", "project_id", session["project_id"], {"payment_status": "paid", "access_status": "active"})
    return {"payment": payment, "credit": credit}


def _safe_legacy_project_id(project_id: str) -> str:
    project_id = (project_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", project_id):
        raise ValueError("Invalid project_id in Stripe metadata.")
    return project_id


def activate_legacy_single_project(project_id: str, stripe_session_id: Optional[str] = None) -> Dict[str, Any]:
    safe_project_id = _safe_legacy_project_id(project_id)
    path = LEGACY_PROJECT_DIR / f"{safe_project_id}.json"
    if not path.exists():
        return {"status": "legacy_project_not_found", "project_id": safe_project_id}
    with path.open("r", encoding="utf-8") as handle:
        project = json.load(handle)
    project["paid"] = True
    project["payment_status"] = "stripe_paid"
    project["stripe_checkout_session_id"] = stripe_session_id or project.get("stripe_checkout_session_id")
    project["paid_at"] = datetime.utcnow().isoformat()
    project["updated_at"] = datetime.utcnow().isoformat()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(project, handle, ensure_ascii=False, indent=2)
    log_activity(project.get("customer_email"), "payment.legacy_single_project_paid", {"project_id": safe_project_id, "stripe_session_id": stripe_session_id})
    return {"status": "legacy_project_paid", "project_id": safe_project_id}


def handle_stripe_webhook(raw_body: bytes, signature: Optional[str]) -> Dict[str, Any]:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not _stripe_ready():
        if production_security_enabled():
            raise RuntimeError("Stripe is not configured. Set STRIPE_SECRET_KEY before production launch.")
        return {"status": "webhook_not_configured", "handled": False}
    if not webhook_secret:
        if production_security_enabled() or stripe_webhook_must_verify():
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is required for webhook verification.")
        return {"status": "webhook_secret_missing", "handled": False}
    if stripe_webhook_must_verify() and not signature:
        raise RuntimeError("Missing Stripe-Signature header.")
    event = stripe.Webhook.construct_event(raw_body, signature or "", webhook_secret)
    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})
    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        checkout_id = metadata.get("checkout_id")
        if checkout_id:
            activated = activate_checkout(checkout_id, obj.get("id"), obj.get("customer_email"))
            return {"status": "handled", "event": event_type, "activated": activated}
        project_id = metadata.get("project_id") or obj.get("client_reference_id")
        if project_id:
            activated = activate_legacy_single_project(project_id, obj.get("id"))
            return {"status": "handled", "event": event_type, "activated": activated}
    if event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        stripe_sub_id = obj.get("id")
        for sub in list_rows("subscriptions"):
            if sub.get("stripe_subscription_id") == stripe_sub_id:
                update_one("subscriptions", "subscription_id", sub["subscription_id"], {"status": "canceled"})
        return {"status": "handled", "event": event_type}
    return {"status": "ignored", "event": event_type}
