"""Company workspace membership and controlled invitation service.

This module intentionally manages company roster governance without silently
expanding project access. Project-level sharing remains a separate capability
because existing project ownership checks must be migrated explicitly rather
than widened through a generic company-membership bypass.

Invitation delivery is manual in this release: a manager receives a one-time
acceptance URL and must transmit it through an approved channel. The raw token
is never persisted; only a SHA-256 digest is stored in Supabase.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from ..production_store import (
    ProductionStoreError,
    first_update,
    insert_row,
    is_configured,
    select_one,
    select_rows,
    uuid_like,
)

TEAM_ROLES = frozenset({"owner", "manager", "editor", "viewer"})
TEAM_MEMBER_STATUSES = frozenset({"active", "suspended"})
INVITATION_STATUSES = frozenset({"pending", "accepted", "revoked", "expired"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_email(value: str | None) -> str:
    return str(value or "").strip().lower()


def _uuid(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text if uuid_like(text) else None


def invite_ttl_hours() -> int:
    raw = os.getenv("DEVBAREUN_TEAM_INVITE_TTL_HOURS", "72")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 72
    return max(1, min(value, 168))


def invitation_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _workspace_url(token: str) -> str:
    base = (os.getenv("PUBLIC_SITE_URL") or "https://devbareun.com").strip().rstrip("/")
    return f"{base}/workspace/?view=team&invite={token}"


def _company_row(company: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "company_id": str(company.get("id") or company.get("company_id") or ""),
        "company_name": str(company.get("company_name") or company.get("name") or "Company workspace"),
        "plan": company.get("plan") or company.get("subscription_plan") or "free",
        "created_at": company.get("created_at"),
    }


def _membership_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "membership_id": str(row.get("id") or row.get("membership_id") or ""),
        "member_email": _normalize_email(row.get("member_email")),
        "company_role": str(row.get("company_role") or "viewer").lower(),
        "status": str(row.get("status") or "active").lower(),
        "joined_at": row.get("joined_at") or row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _invite_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "invitation_id": str(row.get("id") or row.get("invitation_id") or ""),
        "invitee_email": _normalize_email(row.get("invitee_email")),
        "company_role": str(row.get("company_role") or "viewer").lower(),
        "status": str(row.get("status") or "pending").lower(),
        "expires_at": row.get("expires_at"),
        "created_at": row.get("created_at"),
        "accepted_at": row.get("accepted_at"),
    }


def _first_company_for_user(user: Any) -> Optional[Dict[str, Any]]:
    if not is_configured():
        raise ProductionStoreError("Company collaboration requires the Supabase production store.")
    company_id = _uuid(getattr(user, "company_id", None))
    if company_id:
        row = select_one("companies", {"id": company_id})
        if row:
            return row
    profile_id = _uuid(getattr(user, "id", None))
    if profile_id:
        profile = select_one("users_profile", {"id": profile_id})
        profile_company_id = _uuid((profile or {}).get("company_id"))
        if profile_company_id:
            row = select_one("companies", {"id": profile_company_id})
            if row:
                return row
        row = select_one("companies", {"owner_user_id": profile_id})
        if row:
            return row
    email = _normalize_email(getattr(user, "email", None))
    if email:
        row = select_one("companies", {"owner_email": email})
        if row:
            return row
    return None


def _profile_filters(user: Any) -> Iterable[Dict[str, Any]]:
    profile_id = _uuid(getattr(user, "id", None))
    auth_user_id = _uuid(getattr(user, "auth_user_id", None))
    if profile_id:
        yield {"id": profile_id}
    if auth_user_id:
        yield {"auth_user_id": auth_user_id}
    email = _normalize_email(getattr(user, "email", None))
    if email:
        yield {"email": email}


def _set_profile_company(user: Any, company_id: str) -> None:
    for filters in _profile_filters(user):
        updated = first_update("users_profile", filters, {"company_id": company_id, "updated_at": _iso(_now())})
        if updated:
            return
    raise ProductionStoreError("User profile could not be linked to the company workspace.")


def _find_membership(company_id: str, *, user: Any | None = None, email: str | None = None) -> Optional[Dict[str, Any]]:
    normalized_email = _normalize_email(email or getattr(user, "email", None))
    profile_id = _uuid(getattr(user, "id", None)) if user is not None else None
    if profile_id:
        row = select_one("company_memberships", {"company_id": company_id, "user_id": profile_id})
        if row:
            return row
    if normalized_email:
        return select_one("company_memberships", {"company_id": company_id, "member_email": normalized_email})
    return None


def _ensure_owner_membership(company_id: str, user: Any) -> Dict[str, Any]:
    existing = _find_membership(company_id, user=user)
    if existing:
        return existing
    profile_id = _uuid(getattr(user, "id", None))
    if not profile_id:
        raise ProductionStoreError("A persisted user profile is required to own a company workspace.")
    now = _iso(_now())
    return insert_row(
        "company_memberships",
        {
            "company_id": company_id,
            "user_id": profile_id,
            "member_email": _normalize_email(getattr(user, "email", None)),
            "company_role": "owner",
            "status": "active",
            "joined_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )


def company_workspace_for_user(user: Any) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return the caller's workspace and membership without creating records."""
    company = _first_company_for_user(user)
    if not company:
        return None, None
    company_id = _uuid(company.get("id"))
    if not company_id:
        raise ProductionStoreError("Company workspace has an invalid identifier.")
    membership = _find_membership(company_id, user=user)
    if not membership:
        # Existing pre-team company owners are safely backfilled on their first
        # team read; non-owner users never receive implicit membership.
        owner_id = _uuid(company.get("owner_user_id"))
        current_id = _uuid(getattr(user, "id", None))
        owner_email = _normalize_email(company.get("owner_email"))
        if (owner_id and owner_id == current_id) or (owner_email and owner_email == _normalize_email(getattr(user, "email", None))):
            membership = _ensure_owner_membership(company_id, user)
    return company, membership


def bootstrap_workspace(user: Any, company_name: str) -> tuple[Dict[str, Any], Dict[str, Any], bool]:
    """Create exactly one company workspace for a profile that does not have one."""
    if not is_configured():
        raise ProductionStoreError("Company collaboration requires the Supabase production store.")
    normalized_name = " ".join(str(company_name or "").split()).strip()
    if not normalized_name:
        raise ValueError("Company name is required.")
    if len(normalized_name) > 180:
        raise ValueError("Company name must be 180 characters or fewer.")
    company, membership = company_workspace_for_user(user)
    if company:
        if not membership:
            raise PermissionError("Your profile is not an active member of the linked company workspace.")
        return company, membership, False
    profile_id = _uuid(getattr(user, "id", None))
    if not profile_id:
        raise ProductionStoreError("A persisted user profile is required to create a company workspace.")
    now = _iso(_now())
    company = insert_row(
        "companies",
        {
            "owner_user_id": profile_id,
            "owner_email": _normalize_email(getattr(user, "email", None)),
            "name": normalized_name,
            "company_name": normalized_name,
            "plan": getattr(user, "plan", None) or "free",
            "subscription_plan": getattr(user, "plan", None) or "free",
            "created_at": now,
            "updated_at": now,
        },
    )
    company_id = _uuid(company.get("id"))
    if not company_id:
        raise ProductionStoreError("Company workspace creation did not return a UUID identifier.")
    _set_profile_company(user, company_id)
    membership = _ensure_owner_membership(company_id, user)
    return company, membership, True


def require_active_membership(user: Any) -> tuple[Dict[str, Any], Dict[str, Any]]:
    company, membership = company_workspace_for_user(user)
    if not company:
        raise LookupError("No company workspace is linked to this account.")
    if not membership:
        raise PermissionError("You are not a member of this company workspace.")
    status = str(membership.get("status") or "").lower()
    if status != "active":
        raise PermissionError("Your company membership is not active.")
    return company, membership


def can_manage_team(membership: Dict[str, Any] | None) -> bool:
    return bool(membership) and str(membership.get("status") or "").lower() == "active" and str(membership.get("company_role") or "").lower() in {"owner", "manager"}


def list_members(company_id: str) -> list[Dict[str, Any]]:
    rows = select_rows("company_memberships", {"company_id": company_id}, limit=500)
    result = [_membership_row(row) for row in rows]
    return sorted(result, key=lambda item: (item["company_role"] != "owner", item["member_email"]))


def list_invitations(company_id: str) -> list[Dict[str, Any]]:
    rows = select_rows("company_invitations", {"company_id": company_id}, limit=500)
    now = _now()
    items: list[Dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status") or "pending").lower()
        expires = _parse_timestamp(row.get("expires_at"))
        if status == "pending" and expires and expires <= now:
            try:
                first_update("company_invitations", {"id": row.get("id")}, {"status": "expired", "updated_at": _iso(now)})
            except ProductionStoreError:
                pass
            row = {**row, "status": "expired"}
        items.append(_invite_row(row))
    return sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def create_invitation(user: Any, email: str, role: str, expires_in_hours: Optional[int] = None) -> Dict[str, Any]:
    company, membership = require_active_membership(user)
    if not can_manage_team(membership):
        raise PermissionError("Company owner or manager access is required to invite team members.")
    company_id = _uuid(company.get("id"))
    assert company_id
    invitee_email = _normalize_email(email)
    if "@" not in invitee_email or len(invitee_email) > 320:
        raise ValueError("A valid invitation email is required.")
    if invitee_email == _normalize_email(getattr(user, "email", None)):
        raise ValueError("You are already a member of this company workspace.")
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in {"manager", "editor", "viewer"}:
        raise ValueError("Invitations may assign manager, editor or viewer roles only.")
    existing_member = _find_membership(company_id, email=invitee_email)
    if existing_member and str(existing_member.get("status") or "").lower() == "active":
        raise ValueError("This email is already an active company member.")
    for invite in select_rows("company_invitations", {"company_id": company_id, "invitee_email": invitee_email}, limit=25):
        status = str(invite.get("status") or "pending").lower()
        expires = _parse_timestamp(invite.get("expires_at"))
        if status == "pending" and (not expires or expires > _now()):
            raise ValueError("An active invitation already exists for this email.")
    raw_token = secrets.token_urlsafe(32)
    ttl = int(expires_in_hours or invite_ttl_hours())
    ttl = max(1, min(ttl, 168))
    now = _now()
    invitation = insert_row(
        "company_invitations",
        {
            "company_id": company_id,
            "invitee_email": invitee_email,
            "company_role": normalized_role,
            "token_hash": invitation_hash(raw_token),
            "status": "pending",
            "invited_by_user_id": _uuid(getattr(user, "id", None)),
            "expires_at": _iso(now + timedelta(hours=ttl)),
            "created_at": _iso(now),
            "updated_at": _iso(now),
        },
    )
    return {
        "invitation": _invite_row(invitation),
        "invite_url": _workspace_url(raw_token),
        "delivery_mode": "manual",
        "notice": "Copy the invitation URL now. The raw token is not stored and cannot be shown again.",
    }


def accept_invitation(user: Any, token: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    raw_token = str(token or "").strip()
    if len(raw_token) < 24:
        raise ValueError("Invitation token is invalid.")
    invitation = select_one("company_invitations", {"token_hash": invitation_hash(raw_token)})
    if not invitation:
        raise LookupError("Invitation was not found or has already been removed.")
    now = _now()
    status = str(invitation.get("status") or "pending").lower()
    expires = _parse_timestamp(invitation.get("expires_at"))
    if status == "pending" and expires and expires <= now:
        first_update("company_invitations", {"id": invitation.get("id")}, {"status": "expired", "updated_at": _iso(now)})
        raise ValueError("Invitation has expired.")
    if status != "pending":
        raise ValueError("Invitation is no longer active.")
    invitee_email = _normalize_email(invitation.get("invitee_email"))
    if invitee_email != _normalize_email(getattr(user, "email", None)):
        raise PermissionError("Sign in with the invited email address to accept this invitation.")
    company_id = _uuid(invitation.get("company_id"))
    profile_id = _uuid(getattr(user, "id", None))
    if not company_id or not profile_id:
        raise ProductionStoreError("A persisted user profile is required to accept an invitation.")
    current_company = _uuid(getattr(user, "company_id", None))
    if current_company and current_company != company_id:
        raise PermissionError("This account is already linked to another company workspace.")
    company = select_one("companies", {"id": company_id})
    if not company:
        raise LookupError("The company workspace for this invitation no longer exists.")
    existing = _find_membership(company_id, user=user)
    if existing:
        membership = first_update(
            "company_memberships",
            {"id": existing.get("id")},
            {
                "user_id": profile_id,
                "member_email": invitee_email,
                "company_role": invitation.get("company_role") or existing.get("company_role") or "viewer",
                "status": "active",
                "joined_at": existing.get("joined_at") or _iso(now),
                "updated_at": _iso(now),
            },
        ) or existing
    else:
        membership = insert_row(
            "company_memberships",
            {
                "company_id": company_id,
                "user_id": profile_id,
                "member_email": invitee_email,
                "company_role": invitation.get("company_role") or "viewer",
                "status": "active",
                "invited_by_user_id": invitation.get("invited_by_user_id"),
                "joined_at": _iso(now),
                "created_at": _iso(now),
                "updated_at": _iso(now),
            },
        )
    _set_profile_company(user, company_id)
    first_update(
        "company_invitations",
        {"id": invitation.get("id")},
        {"status": "accepted", "accepted_by_user_id": profile_id, "accepted_at": _iso(now), "updated_at": _iso(now)},
    )
    return company, membership


def revoke_invitation(user: Any, invitation_id: str) -> Dict[str, Any]:
    company, membership = require_active_membership(user)
    if not can_manage_team(membership):
        raise PermissionError("Company owner or manager access is required to revoke invitations.")
    company_id = _uuid(company.get("id"))
    invitation = select_one("company_invitations", {"id": invitation_id})
    if not invitation or _uuid(invitation.get("company_id")) != company_id:
        raise LookupError("Invitation not found.")
    if str(invitation.get("status") or "").lower() != "pending":
        raise ValueError("Only pending invitations can be revoked.")
    return first_update("company_invitations", {"id": invitation_id}, {"status": "revoked", "updated_at": _iso(_now())}) or invitation


def update_member(user: Any, membership_id: str, *, role: Optional[str], status: Optional[str]) -> Dict[str, Any]:
    company, actor_membership = require_active_membership(user)
    if not can_manage_team(actor_membership):
        raise PermissionError("Company owner or manager access is required to update members.")
    company_id = _uuid(company.get("id"))
    target = select_one("company_memberships", {"id": membership_id})
    if not target or _uuid(target.get("company_id")) != company_id:
        raise LookupError("Company member not found.")
    actor_role = str(actor_membership.get("company_role") or "").lower()
    target_role = str(target.get("company_role") or "").lower()
    if target_role == "owner":
        raise PermissionError("The company owner cannot be changed through the team workspace.")
    if actor_role == "manager" and target_role == "manager":
        raise PermissionError("A manager cannot change another manager.")
    patch: Dict[str, Any] = {"updated_at": _iso(_now())}
    if role is not None:
        normalized_role = str(role).strip().lower()
        if normalized_role not in {"manager", "editor", "viewer"}:
            raise ValueError("Member role must be manager, editor or viewer.")
        if actor_role == "manager" and normalized_role == "manager":
            raise PermissionError("Only the company owner can grant manager access.")
        patch["company_role"] = normalized_role
    if status is not None:
        normalized_status = str(status).strip().lower()
        if normalized_status not in TEAM_MEMBER_STATUSES:
            raise ValueError("Member status must be active or suspended.")
        patch["status"] = normalized_status
    if len(patch) == 1:
        raise ValueError("Provide a role or status change.")
    return first_update("company_memberships", {"id": membership_id}, patch) or target


def company_team_payload(user: Any) -> Dict[str, Any]:
    company, membership = company_workspace_for_user(user)
    if not company:
        return {
            "workspace": None,
            "membership": None,
            "members": [],
            "invitations": [],
            "can_manage_team": False,
            "manual_invites": True,
        }
    if not membership:
        raise PermissionError("You are not a member of the linked company workspace.")
    company_id = _uuid(company.get("id"))
    assert company_id
    return {
        "workspace": _company_row(company),
        "membership": _membership_row(membership),
        "members": list_members(company_id),
        "invitations": list_invitations(company_id) if can_manage_team(membership) else [],
        "can_manage_team": can_manage_team(membership),
        "manual_invites": True,
    }
