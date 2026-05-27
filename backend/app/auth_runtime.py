
"""
DevBareun Auth Runtime
v1.3.8 — Real Auth + Protected Workspace + Usage Gate

This module provides Supabase-compatible auth helpers while keeping
local/pilot fallback behavior for environments where Supabase keys
are not configured yet.
"""
from __future__ import annotations

import os
import time
import secrets
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .security_runtime import devbareun_domain_admin_allowed

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


@dataclass
class AuthUser:
    email: str
    user_id: str
    company_id: Optional[str] = None
    plan: str = "guest"
    credits_remaining: int = 0
    is_admin: bool = False


class AuthError(Exception):
    pass


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Pilot in-memory session store. Production should rely on Supabase Auth/JWT.
_PILOT_SESSIONS: Dict[str, AuthUser] = {}


PLAN_LIMITS: Dict[str, int] = {
    "guest": 0,
    "free": 0,
    "single": 1,
    "plus": 5,
    "pro": 20,
}


def plan_credit_limit(plan: Optional[str]) -> int:
    return PLAN_LIMITS.get((plan or "guest").lower(), 0)


def consume_pilot_credit(token: Optional[str]) -> Dict[str, Any]:
    """Consume one in-memory pilot credit.

    Production subscription usage should be enforced through the database/Stripe
    ledger. This helper keeps the staging workspace realistic before those
    providers are fully wired.
    """
    if not token or token not in _PILOT_SESSIONS:
        return {"consumed": False, "reason": "not_a_pilot_session"}
    user = _PILOT_SESSIONS[token]
    if int(user.credits_remaining or 0) <= 0:
        raise AuthError("No analysis credits available for this workspace.")
    user.credits_remaining = int(user.credits_remaining or 0) - 1
    return {"consumed": True, "credits_remaining": user.credits_remaining, "plan": user.plan}


def set_pilot_plan(token: Optional[str], plan: str) -> Dict[str, Any]:
    if not token or token not in _PILOT_SESSIONS:
        return {"updated": False, "reason": "not_a_pilot_session"}
    user = _PILOT_SESSIONS[token]
    user.plan = plan
    user.credits_remaining = plan_credit_limit(plan)
    return {"updated": True, "plan": user.plan, "credits_remaining": user.credits_remaining}


def _pilot_enabled() -> bool:
    return os.getenv("DEVBAREUN_AUTH_MODE", "pilot").lower() in {"pilot", "mock", "local"}


def create_pilot_session(email: str, plan: str = "plus") -> Dict[str, Any]:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise AuthError("Valid email is required.")

    token = "dbr_" + secrets.token_urlsafe(32)
    credits = 20 if plan == "pro" else 5 if plan == "plus" else 1
    user = AuthUser(
        email=email,
        user_id="USR-" + secrets.token_hex(6).upper(),
        company_id="CMP-" + secrets.token_hex(5).upper(),
        plan=plan,
        credits_remaining=credits,
        is_admin=devbareun_domain_admin_allowed() and email.endswith("@devbareun.com"),
    )
    _PILOT_SESSIONS[token] = user
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 60 * 60 * 24 * 7,
        "user": user.__dict__,
    }


def get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def verify_supabase_token(token: str) -> AuthUser:
    if not token:
        raise AuthError("Missing access token.")

    if token in _PILOT_SESSIONS:
        return _PILOT_SESSIONS[token]

    if _pilot_enabled() and token.startswith("dbr_"):
        raise AuthError("Invalid or expired pilot session.")

    if not SUPABASE_URL or not SUPABASE_ANON_KEY or httpx is None:
        raise AuthError("Supabase auth is not configured.")

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers)

    if resp.status_code >= 400:
        raise AuthError("Invalid Supabase session.")

    data = resp.json()
    email = data.get("email") or (data.get("user_metadata") or {}).get("email")
    user_id = data.get("id") or data.get("sub")
    if not email or not user_id:
        raise AuthError("Invalid Supabase user payload.")

    meta = data.get("user_metadata") or {}
    return AuthUser(
        email=email,
        user_id=user_id,
        company_id=meta.get("company_id"),
        plan=meta.get("plan", "free"),
        credits_remaining=int(meta.get("credits_remaining", 0) or 0),
        is_admin=bool(meta.get("is_admin", False)),
    )


def auth_user_payload(user: AuthUser) -> Dict[str, Any]:
    return {
        "email": user.email,
        "user_id": user.user_id,
        "company_id": user.company_id,
        "plan": user.plan,
        "credits_remaining": user.credits_remaining,
        "is_admin": user.is_admin,
    }
