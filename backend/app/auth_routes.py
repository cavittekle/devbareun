
"""
DevBareun Auth Routes
v1.3.5 — Real Auth + Protected Workspace
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel

from .security_runtime import bool_env, production_security_enabled
from .auth_runtime import (
    AuthError,
    create_pilot_session,
    verify_supabase_token,
    get_bearer_token,
    auth_user_payload,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
AUTH_COOKIE = "devbareun_auth"
PILOT_ADMIN_FILE = Path(__file__).resolve().parent.parent / "data" / "saas" / "pilot_admin_account.json"


def _set_auth_cookie(response: Response, token: str | None) -> None:
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


class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    plan: Optional[str] = "plus"


def _pilot_admin_account() -> dict | None:
    if not PILOT_ADMIN_FILE.exists():
        return None
    try:
        data = json.loads(PILOT_ADMIN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    if not email or not password:
        return None
    return {
        "email": email,
        "password": password,
        "plan": str(data.get("plan") or "pro").strip().lower() or "pro",
    }


@router.post("/pilot-login")
async def pilot_login(payload: LoginRequest, response: Response):
    """
    Pilot login for staging/demo environments.
    Production should use Supabase Auth on the frontend and pass the Supabase JWT.
    """
    if production_security_enabled():
        raise HTTPException(status_code=403, detail="Pilot login is disabled in production security mode.")
    try:
        admin_account = _pilot_admin_account()
        email = str(payload.email or "").strip().lower()
        if admin_account and email == admin_account["email"]:
            if str(payload.password or "") != admin_account["password"]:
                raise AuthError("Pilot admin password is incorrect.")
            session = create_pilot_session(email, admin_account["plan"], force_admin=True)
        else:
            session = create_pilot_session(email, payload.plan or "plus")
        _set_auth_cookie(response, session.get("access_token"))
        return session
    except AuthError as exc:
        raise HTTPException(status_code=400, detail={"error": "pilot_login_failed", "message": "Pilot login could not be completed."}) from exc


@router.get("/me")
async def me(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)):
    token = get_bearer_token(authorization) or auth_cookie
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    try:
        user = await verify_supabase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or expired session."}) from exc
    return {"user": auth_user_payload(user), "authenticated": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE, path="/")
    return {"ok": True}
