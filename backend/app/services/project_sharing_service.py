"""Explicit project-level access for company workspace members.

Company membership alone does not grant project access.  A project owner (or a
project manager explicitly granted access) must create an active
``project_access_grants`` record before another company member can read or
operate on a project.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from ..production_store import ProductionStoreError, first_update, insert_row, is_configured, select_one, select_rows, uuid_like

PROJECT_ROLES = frozenset({"viewer", "editor", "manager"})
PROJECT_GRANT_STATUSES = frozenset({"active", "revoked"})

# Owner is implicit through project ownership. All other roles must be explicit.
RESOURCE_ROLES: dict[str, frozenset[str]] = {
    "projects": frozenset({"viewer", "editor", "manager", "owner"}),
    "dashboard": frozenset({"viewer", "editor", "manager", "owner"}),
    "analysis_view": frozenset({"viewer", "editor", "manager", "owner"}),
    "reports": frozenset({"viewer", "editor", "manager", "owner"}),
    "project_activity": frozenset({"viewer", "editor", "manager", "owner"}),
    "project_update": frozenset({"editor", "manager", "owner"}),
    "uploads": frozenset({"editor", "manager", "owner"}),
    "analysis_run": frozenset({"editor", "manager", "owner"}),
    "reports_generate": frozenset({"editor", "manager", "owner"}),
    "project_access_manage": frozenset({"manager", "owner"}),
    "project_delete": frozenset({"owner"}),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uuid(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if uuid_like(text) else None


def _email(value: Any) -> str:
    return str(value or "").strip().lower()


def _project_id(project: Dict[str, Any]) -> str | None:
    return _uuid(project.get("id") or project.get("project_id"))


def _company_id(project: Dict[str, Any]) -> str | None:
    return _uuid(project.get("company_id"))


def _owner_matches(project: Dict[str, Any], user: Any) -> bool:
    candidates = {
        str(getattr(user, "id", "") or "").lower(),
        str(getattr(user, "auth_user_id", "") or "").lower(),
        _email(getattr(user, "email", "")),
    }
    owners = {
        str(project.get("user_id") or "").lower(),
        str(project.get("owner_user_id") or "").lower(),
        _email(project.get("owner_email")),
    }
    return bool(candidates.intersection(owners) - {""})


def _active_company_membership(company_id: str, user: Any) -> Dict[str, Any] | None:
    user_id = _uuid(getattr(user, "id", None))
    if not company_id or not user_id or not is_configured():
        return None
    membership = select_one("company_memberships", {"company_id": company_id, "user_id": user_id})
    if not membership:
        return None
    if str(membership.get("status") or "").lower() != "active":
        return None
    return membership


def project_access_role(project: Dict[str, Any], user: Any) -> str | None:
    """Resolve the caller's project role without widening company membership.

    This helper deliberately returns ``None`` for a same-company member without
    an explicit active grant.
    """
    if _owner_matches(project, user):
        return "owner"
    if not is_configured():
        return None
    project_id = _project_id(project)
    company_id = _company_id(project)
    user_id = _uuid(getattr(user, "id", None))
    if not project_id or not company_id or not user_id:
        return None
    profile_company = _uuid(getattr(user, "company_id", None))
    if profile_company and profile_company != company_id:
        return None
    if not _active_company_membership(company_id, user):
        return None
    grant = select_one("project_access_grants", {"project_id": project_id, "user_id": user_id})
    if not grant or str(grant.get("status") or "").lower() != "active":
        return None
    role = str(grant.get("project_role") or "").lower()
    return role if role in PROJECT_ROLES else None


def can_access_project_resource(project: Dict[str, Any], user: Any, section: str) -> bool:
    role = project_access_role(project, user)
    allowed = RESOURCE_ROLES.get(str(section or "projects").strip().lower(), frozenset())
    return bool(role and role in allowed)


def list_accessible_projects(user: Any, *, limit: int = 500) -> list[Dict[str, Any]]:
    """Return owned projects plus explicit active grants for a customer user."""
    if not is_configured():
        return []
    user_id = _uuid(getattr(user, "id", None))
    email = _email(getattr(user, "email", None))
    rows: list[Dict[str, Any]] = []
    if user_id:
        rows.extend(select_rows("projects", {"user_id": user_id}, limit=limit))
    if email:
        rows.extend(select_rows("projects", {"owner_email": email}, limit=limit))
    if user_id:
        grants = select_rows("project_access_grants", {"user_id": user_id, "status": "active"}, limit=limit)
        for grant in grants:
            project_id = _uuid(grant.get("project_id"))
            if not project_id:
                continue
            project = select_one("projects", {"id": project_id})
            if project and can_access_project_resource(project, user, "projects"):
                rows.append(project)
    unique: dict[str, Dict[str, Any]] = {}
    for row in rows:
        identifier = str(row.get("id") or row.get("project_id") or "")
        if identifier:
            unique[identifier] = row
    return sorted(unique.values(), key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)


def _require_project_manager(project: Dict[str, Any], actor: Any) -> tuple[str, str]:
    project_id = _project_id(project)
    company_id = _company_id(project)
    if not project_id or not company_id:
        raise ValueError("Project must be linked to a company workspace before access can be shared.")
    if not can_access_project_resource(project, actor, "project_access_manage"):
        raise PermissionError("Project owner or project manager access is required.")
    return project_id, company_id


def _membership_for_company(company_id: str, membership_id: str) -> Dict[str, Any]:
    if not _uuid(membership_id):
        raise LookupError("Company member was not found.")
    membership = select_one("company_memberships", {"id": membership_id})
    if not membership or _uuid(membership.get("company_id")) != company_id:
        raise LookupError("Company member was not found.")
    if str(membership.get("status") or "").lower() != "active":
        raise ValueError("Only active company members can receive project access.")
    if not _uuid(membership.get("user_id")):
        raise ValueError("Company member must accept the invitation before project access can be granted.")
    return membership


def _grant_payload(row: Dict[str, Any], membership: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "grant_id": str(row.get("id") or row.get("grant_id") or ""),
        "membership_id": str(row.get("membership_id") or ""),
        "member_email": _email((membership or {}).get("member_email") or row.get("member_email")),
        "project_role": str(row.get("project_role") or "viewer").lower(),
        "status": str(row.get("status") or "active").lower(),
        "granted_at": row.get("granted_at") or row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def list_project_access(project: Dict[str, Any], actor: Any) -> list[Dict[str, Any]]:
    project_id, company_id = _require_project_manager(project, actor)
    grants = select_rows("project_access_grants", {"project_id": project_id}, limit=500)
    rows: list[Dict[str, Any]] = []
    for grant in grants:
        membership = select_one("company_memberships", {"id": grant.get("membership_id")}) if grant.get("membership_id") else None
        if membership and _uuid(membership.get("company_id")) == company_id:
            rows.append(_grant_payload(grant, membership))
    return sorted(rows, key=lambda item: (item["member_email"], item["project_role"]))


def grant_project_access(project: Dict[str, Any], actor: Any, *, membership_id: str, project_role: str) -> Dict[str, Any]:
    project_id, company_id = _require_project_manager(project, actor)
    role = str(project_role or "").strip().lower()
    if role not in PROJECT_ROLES:
        raise ValueError("Project role must be manager, editor or viewer.")
    membership = _membership_for_company(company_id, membership_id)
    target_user_id = _uuid(membership.get("user_id"))
    assert target_user_id
    if _owner_matches(project, type("Target", (), {"id": target_user_id, "auth_user_id": "", "email": membership.get("member_email")})()):
        raise ValueError("The project owner already has full access and does not need a grant.")
    now = _now()
    existing = select_one("project_access_grants", {"project_id": project_id, "user_id": target_user_id})
    payload = {
        "project_id": project_id,
        "company_id": company_id,
        "membership_id": _uuid(membership.get("id")),
        "user_id": target_user_id,
        "member_email": _email(membership.get("member_email")),
        "project_role": role,
        "status": "active",
        "granted_by_user_id": _uuid(getattr(actor, "id", None)),
        "granted_at": now,
        "updated_at": now,
    }
    if existing:
        grant = first_update("project_access_grants", {"id": existing.get("id")}, payload) or existing
    else:
        grant = insert_row("project_access_grants", {**payload, "created_at": now})
    return _grant_payload(grant, membership)


def update_project_access(project: Dict[str, Any], actor: Any, *, grant_id: str, project_role: str | None = None, status: str | None = None) -> Dict[str, Any]:
    project_id, company_id = _require_project_manager(project, actor)
    grant = select_one("project_access_grants", {"id": grant_id})
    if not grant or _uuid(grant.get("project_id")) != project_id or _uuid(grant.get("company_id")) != company_id:
        raise LookupError("Project access grant was not found.")
    patch: Dict[str, Any] = {"updated_at": _now()}
    if project_role is not None:
        role = str(project_role).strip().lower()
        if role not in PROJECT_ROLES:
            raise ValueError("Project role must be manager, editor or viewer.")
        patch["project_role"] = role
    if status is not None:
        normalized = str(status).strip().lower()
        if normalized not in PROJECT_GRANT_STATUSES:
            raise ValueError("Project grant status must be active or revoked.")
        patch["status"] = normalized
    if len(patch) == 1:
        raise ValueError("Provide a project role or status change.")
    updated = first_update("project_access_grants", {"id": grant.get("id")}, patch) or grant
    membership = select_one("company_memberships", {"id": updated.get("membership_id")}) if updated.get("membership_id") else None
    return _grant_payload(updated, membership)


def revoke_project_access(project: Dict[str, Any], actor: Any, *, grant_id: str) -> Dict[str, Any]:
    return update_project_access(project, actor, grant_id=grant_id, status="revoked")
