
"""
DevBareun Auth Routes
v1.3.5 — Real Auth + Protected Workspace
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
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


class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    plan: Optional[str] = "plus"


@router.post("/pilot-login")
async def pilot_login(payload: LoginRequest):
    """
    Pilot login for staging/demo environments.
    Production should use Supabase Auth on the frontend and pass the Supabase JWT.
    """
    if production_security_enabled():
        raise HTTPException(status_code=403, detail="Pilot login is disabled in production security mode.")
    try:
        return create_pilot_session(payload.email, payload.plan or "plus")
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/me")
async def me(authorization: Optional[str] = Header(None)):
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    try:
        user = await verify_supabase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return {"user": auth_user_payload(user), "authenticated": True}


@router.post("/logout")
async def logout():
    return {"ok": True}
