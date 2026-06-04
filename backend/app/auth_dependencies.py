from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from .auth_runtime import AuthError, AuthUser, get_bearer_token, verify_supabase_token
from .production_store import ProductionStoreError, first_existing, insert_row, is_configured, select_one, uuid_like
from .security_runtime import bool_env, production_security_enabled


@dataclass
class CurrentUser:
    id: str
    auth_user_id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    status: str = "active"
    company_id: Optional[str] = None
    plan: str = "free"
    is_admin: bool = False

    def payload(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "auth_user_id": self.auth_user_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "status": self.status,
            "company_id": self.company_id,
            "plan": self.plan,
            "is_admin": self.is_admin,
        }


def env_flag(name: str, default: bool = False) -> bool:
    return bool_env(name, default)


def production_security() -> bool:
    return production_security_enabled()


def local_store_enabled() -> bool:
    return bool_env("DEVBAREUN_ENABLE_LOCAL_STORE", False) and not production_security_enabled()


def _uuid_or_none(value: str | None) -> Optional[str]:
    if not value:
        return None
    try:
        return str(UUID(str(value)))
    except Exception:
        return None


def _clean_401(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"error": "unauthorized", "message": message})


def _clean_403(message: str) -> HTTPException:
    return HTTPException(status_code=403, detail={"error": "forbidden", "message": message})


def _profile_from_auth_user(auth_user: AuthUser) -> Optional[Dict[str, Any]]:
    if not is_configured():
        return None
    filters = []
    auth_uuid = _uuid_or_none(auth_user.user_id)
    if auth_uuid:
        filters.append({"auth_user_id": auth_uuid})
    filters.append({"email": auth_user.email})
    profile = first_existing("users_profile", filters)
    if profile:
        return profile
    payload: Dict[str, Any] = {
        "email": auth_user.email,
        "full_name": None,
        "role": "admin" if auth_user.is_admin else "user",
        "status": "active",
    }
    if auth_uuid:
        payload["auth_user_id"] = auth_uuid
    try:
        return insert_row("users_profile", payload)
    except ProductionStoreError:
        return None


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    token = get_bearer_token(authorization)
    if not token:
        raise _clean_401("Missing bearer token.")
    try:
        auth_user = await verify_supabase_token(token)
    except AuthError as exc:
        raise _clean_401(str(exc)) from exc

    profile = _profile_from_auth_user(auth_user)
    role = str((profile or {}).get("role") or ("admin" if auth_user.is_admin else "user")).lower()
    status = str((profile or {}).get("status") or "active").lower()
    if status != "active":
        raise _clean_403("User account is not active.")

    user_id = str((profile or {}).get("id") or auth_user.user_id)
    return CurrentUser(
        id=user_id,
        auth_user_id=str(auth_user.user_id),
        email=auth_user.email,
        full_name=(profile or {}).get("full_name"),
        role=role,
        status=status,
        company_id=str((profile or {}).get("company_id") or auth_user.company_id or "") or None,
        plan=auth_user.plan,
        is_admin=bool(auth_user.is_admin or role == "admin"),
    )


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_admin and current_user.role != "admin":
        raise _clean_403("Admin role is required.")
    return current_user


def _project_filters(project_id: str) -> list[Dict[str, Any]]:
    filters: list[Dict[str, Any]] = []
    if uuid_like(project_id):
        filters.append({"id": project_id})
    filters.append({"project_id": project_id})
    return filters


def _project_belongs_to_user(project: Dict[str, Any], user: CurrentUser) -> bool:
    if user.is_admin:
        return True
    candidates = {
        str(user.id).lower(),
        str(user.auth_user_id).lower(),
        str(user.email).lower(),
    }
    owner_values = {
        str(project.get("user_id") or "").lower(),
        str(project.get("owner_user_id") or "").lower(),
        str(project.get("uploaded_by_user_id") or "").lower(),
        str(project.get("owner_email") or "").lower(),
    }
    return bool(candidates.intersection(owner_values))


async def require_project_owner(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    if is_configured():
        try:
            project = first_existing("projects", _project_filters(project_id))
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": str(exc)}) from exc
        if not project:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Project not found."})
        if not _project_belongs_to_user(project, current_user):
            raise _clean_403("You can access only your own project.")
        return project

    if local_store_enabled():
        from .saas_store import find_one

        project = find_one("projects", project_id=project_id)
        if not project:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Project not found."})
        if not _project_belongs_to_user(project, current_user):
            raise _clean_403("You can access only your own project.")
        return project

    if production_security_enabled():
        raise HTTPException(
            status_code=503,
            detail={"error": "database_not_configured", "message": "Production security requires Supabase PostgreSQL configuration."},
        )
    raise HTTPException(
        status_code=503,
        detail={"error": "local_store_disabled", "message": "Enable DEVBAREUN_ENABLE_LOCAL_STORE=true for local development fallback."},
    )
