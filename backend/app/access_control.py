"""Canonical role and panel-permission policy for DevBareun.

All backend routes must use this module instead of treating every staff role as
an unrestricted administrator. The policy separates customer workspace access
from the internal Super Admin panel and keeps the legacy ``admin``/``user``
role aliases readable during migration.
"""
from __future__ import annotations

from typing import FrozenSet, Mapping

CUSTOMER_ROLE = "customer"
OWNER_ROLE = "owner"
STAFF_ROLES: FrozenSet[str] = frozenset({"owner", "support", "analyst", "finance", "operator"})
ALL_ROLES: FrozenSet[str] = frozenset({CUSTOMER_ROLE, *STAFF_ROLES})

# ``operations`` is intentionally separate from projects/reports. It controls
# worker queue visibility and explicit retry actions, which can affect all
# customer jobs and therefore must not be granted to support or finance.
SUPER_ADMIN_PERMISSIONS: Mapping[str, FrozenSet[str]] = {
    "owner": frozenset({
        "overview", "customers", "projects", "uploads", "reports", "payments", "credits",
        "support", "activity", "audit", "staff", "notes", "operations", "privacy",
    }),
    "support": frozenset({"overview", "customers", "support", "activity", "notes"}),
    "analyst": frozenset({"overview", "projects", "uploads", "reports", "activity"}),
    "finance": frozenset({"overview", "payments", "credits", "activity"}),
    "operator": frozenset({"overview", "projects", "reports", "activity", "operations"}),
}


# Explicit aliases are only accepted while older profile rows are migrated.
_ROLE_ALIASES = {"admin": OWNER_ROLE, "user": CUSTOMER_ROLE}


def normalize_role(role: str | None, is_admin: bool = False) -> str:
    """Return a canonical role without silently widening a recognised role."""
    value = str(role or "").strip().lower()
    value = _ROLE_ALIASES.get(value, value)
    if value in ALL_ROLES:
        return value
    return OWNER_ROLE if is_admin else CUSTOMER_ROLE


def is_staff_role(role: str | None, is_admin: bool = False) -> bool:
    return normalize_role(role, is_admin) in STAFF_ROLES


def has_permission(role: str | None, section: str, is_admin: bool = False) -> bool:
    """Check a canonical internal-panel capability.

    Customers have no Super Admin capability. Owners retain all permissions;
    all other staff roles receive only their explicitly listed modules.
    """
    normalized = normalize_role(role, is_admin)
    return str(section or "").strip().lower() in SUPER_ADMIN_PERMISSIONS.get(normalized, frozenset())


def permissions_for(role: str | None, is_admin: bool = False) -> list[str]:
    return sorted(SUPER_ADMIN_PERMISSIONS.get(normalize_role(role, is_admin), frozenset()))


def can_access_project_scope(role: str | None, section: str, is_admin: bool = False) -> bool:
    """Return whether a staff role may use a scoped cross-customer resource.

    Customer collaboration is handled by explicit project grants elsewhere.
    Staff permissions map resource actions to the narrowest existing panel
    capability; destructive project/share mutations remain owner-only.
    """
    normalized = normalize_role(role, is_admin)
    if normalized == OWNER_ROLE:
        return True
    action = str(section or "projects").strip().lower()
    panel = {
        "projects": "projects", "dashboard": "projects", "analysis_view": "projects",
        "analysis_run": "projects", "reports": "reports", "reports_generate": "reports",
        "uploads": "uploads", "upload_list": "uploads",
    }.get(action, action)
    if action in {"project_update", "project_delete", "project_access_manage"}:
        return False
    return is_staff_role(normalized) and has_permission(normalized, panel)


def can_operate_analysis_jobs(role: str | None, is_admin: bool = False) -> bool:
    return has_permission(role, "operations", is_admin)
