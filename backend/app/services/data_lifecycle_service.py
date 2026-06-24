"""Privacy-safe data lifecycle policy and request helpers.

This module deliberately separates *requesting/reviewing* a privacy action from
physical data destruction. Destructive storage/database purges require a later,
explicitly reviewed execution step so invoices, audit records and backups are
not accidentally erased by a browser request.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional


REQUEST_TYPES = frozenset({"export", "erasure"})
SCOPES = frozenset({"account", "project"})
ACTIVE_STATUSES = frozenset({"requested", "in_review", "approved"})
CUSTOMER_VISIBLE_STATUSES = frozenset({"requested", "in_review", "approved", "rejected", "cancelled", "completed"})
REVIEW_STATUSES = frozenset({"in_review", "approved", "rejected"})
ERASURE_CONFIRMATION = "ERASE MY DATA"


@dataclass(frozen=True)
class DataLifecyclePolicy:
    soft_delete_retention_days: int
    erasure_grace_days: int
    export_request_ttl_days: int
    auto_purge_enabled: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "soft_delete_retention_days": self.soft_delete_retention_days,
            "erasure_grace_days": self.erasure_grace_days,
            "export_request_ttl_days": self.export_request_ttl_days,
            "auto_purge_enabled": self.auto_purge_enabled,
            "automatic_physical_purge": False,
            "scope": "privacy_safe_request_workflow",
        }


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _bounded_int(raw: str | None, *, default: int, minimum: int, maximum: int, label: str) -> int:
    try:
        value = int(str(raw if raw is not None else default).strip())
    except Exception as exc:
        raise ValueError(f"{label} must be an integer.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return value


def policy_from_env(env: Optional[Dict[str, str]] = None) -> DataLifecyclePolicy:
    values = os.environ if env is None else env
    return DataLifecyclePolicy(
        soft_delete_retention_days=_bounded_int(
            values.get("DEVBAREUN_SOFT_DELETE_RETENTION_DAYS"),
            default=30,
            minimum=7,
            maximum=365,
            label="DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
        ),
        erasure_grace_days=_bounded_int(
            values.get("DEVBAREUN_ERASURE_GRACE_DAYS"),
            default=14,
            minimum=1,
            maximum=90,
            label="DEVBAREUN_ERASURE_GRACE_DAYS",
        ),
        export_request_ttl_days=_bounded_int(
            values.get("DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS"),
            default=7,
            minimum=1,
            maximum=30,
            label="DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
        ),
        # Kept for explicit operator visibility. This release does not provide
        # an automatic destructive purge worker, so callers must not infer one.
        auto_purge_enabled=_bool(values.get("DEVBAREUN_AUTO_PURGE_ENABLED"), False),
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def soft_delete_schedule(*, now: Optional[datetime] = None, policy: Optional[DataLifecyclePolicy] = None) -> Dict[str, str]:
    current = now or utc_now()
    retention = policy or policy_from_env()
    return {
        "deleted_at": iso_utc(current),
        "purge_after_at": iso_utc(current + timedelta(days=retention.soft_delete_retention_days)),
        "retention_status": "soft_deleted",
    }


def normalize_request_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in REQUEST_TYPES:
        raise ValueError("request_type must be export or erasure.")
    return normalized


def normalize_scope(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in SCOPES:
        raise ValueError("scope must be account or project.")
    return normalized


def validate_request_scope(scope: str, project_id: Optional[str]) -> tuple[str, Optional[str]]:
    normalized_scope = normalize_scope(scope)
    normalized_project_id = str(project_id or "").strip() or None
    if normalized_scope == "project" and not normalized_project_id:
        raise ValueError("project_id is required for a project-scoped privacy request.")
    if normalized_scope == "account" and normalized_project_id:
        raise ValueError("project_id is not allowed for an account-scoped privacy request.")
    return normalized_scope, normalized_project_id


def validate_erasure_confirmation(confirmation: str | None) -> None:
    if str(confirmation or "").strip().upper() != ERASURE_CONFIRMATION:
        raise ValueError(f"Erasure requests require confirmation: {ERASURE_CONFIRMATION}")


def request_deadlines(request_type: str, *, now: Optional[datetime] = None, policy: Optional[DataLifecyclePolicy] = None) -> Dict[str, Optional[str]]:
    current = now or utc_now()
    retention = policy or policy_from_env()
    kind = normalize_request_type(request_type)
    if kind == "export":
        return {
            "grace_expires_at": None,
            "request_expires_at": iso_utc(current + timedelta(days=retention.export_request_ttl_days)),
            "scheduled_purge_at": None,
        }
    return {
        "grace_expires_at": iso_utc(current + timedelta(days=retention.erasure_grace_days)),
        "request_expires_at": None,
        "scheduled_purge_at": None,
    }


def request_payload(
    *,
    lifecycle_request_id: str,
    requester_email: str,
    requester_user_id: Optional[str],
    request_type: str,
    scope: str,
    project_id: Optional[str],
    reason: Optional[str],
    request_id: Optional[str],
    now: Optional[datetime] = None,
    policy: Optional[DataLifecyclePolicy] = None,
) -> Dict[str, Any]:
    kind = normalize_request_type(request_type)
    normalized_scope, normalized_project_id = validate_request_scope(scope, project_id)
    deadlines = request_deadlines(kind, now=now, policy=policy)
    current = now or utc_now()
    return {
        "lifecycle_request_id": str(lifecycle_request_id),
        "requester_email": str(requester_email).strip().lower(),
        "requester_user_id": str(requester_user_id or "").strip() or None,
        "request_type": kind,
        "scope": normalized_scope,
        "project_id": normalized_project_id,
        "reason": str(reason or "").strip()[:1000] or None,
        "status": "requested",
        "grace_expires_at": deadlines["grace_expires_at"],
        "request_expires_at": deadlines["request_expires_at"],
        "scheduled_purge_at": deadlines["scheduled_purge_at"],
        "requested_at": iso_utc(current),
        "request_id": str(request_id or "").strip()[:180] or None,
        "reviewed_at": None,
        "reviewed_by": None,
        "review_note": None,
        "completed_at": None,
        "cancelled_at": None,
        "metadata": {
            "schema_version": 1,
            "automatic_physical_purge": False,
        },
    }


def is_active_request(row: Dict[str, Any]) -> bool:
    return str((row or {}).get("status") or "").strip().lower() in ACTIVE_STATUSES


def same_request_scope(row: Dict[str, Any], *, request_type: str, scope: str, project_id: Optional[str]) -> bool:
    return (
        str(row.get("request_type") or "").lower() == normalize_request_type(request_type)
        and str(row.get("scope") or "").lower() == normalize_scope(scope)
        and str(row.get("project_id") or "") == str(project_id or "")
    )


def row_owned_by(row: Dict[str, Any], *, user_id_candidates: Iterable[str], email: str) -> bool:
    normalized_email = str(email or "").strip().lower()
    if str(row.get("requester_email") or "").strip().lower() == normalized_email:
        return True
    candidates = {str(item or "").strip().lower() for item in user_id_candidates if str(item or "").strip()}
    requester_id = str(row.get("requester_user_id") or "").strip().lower()
    return bool(requester_id and requester_id in candidates)


def customer_safe_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return request state without internal review metadata or export paths."""
    allowed = {
        "lifecycle_request_id", "request_type", "scope", "project_id", "status",
        "reason", "requested_at", "request_expires_at", "grace_expires_at",
        "scheduled_purge_at", "reviewed_at", "completed_at", "cancelled_at",
    }
    output = {key: value for key, value in dict(row or {}).items() if key in allowed}
    output["automatic_physical_purge"] = False
    return output


def admin_safe_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Keep review data but never surface raw export payloads or storage paths."""
    hidden = {
        "export_payload", "export_storage_path", "storage_path", "signed_url",
        "download_url", "public_url", "requester_user_id", "metadata",
    }
    return {key: value for key, value in dict(row or {}).items() if key not in hidden}
