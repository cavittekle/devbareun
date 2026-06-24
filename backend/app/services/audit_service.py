"""Append-only audit-event helpers.

Audit records intentionally exclude request credentials and raw user payloads.
When Supabase is configured, the database RPC creates the chained integrity
record atomically. Local/development mode returns a shaped event for tests but
does not claim durable audit storage.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, Optional

from ..audit_context import current_audit_context
from ..production_store import ProductionStoreError, call_rpc, is_configured
from ..saas_ids import make_public_id

_SECRET_KEY_RE = re.compile(r"(?:authorization|cookie|token|secret|password|api[_-]?key|service[_-]?role|jwt)", re.I)
_MAX_DEPTH = 5
_MAX_ITEMS = 40
_MAX_TEXT = 1200


class AuditWriteError(RuntimeError):
    """Raised only when callers explicitly require a durable audit event."""


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    return text[:_MAX_TEXT] + "…" if len(text) > _MAX_TEXT else text


def sanitize_metadata(value: Any, *, depth: int = 0) -> Any:
    """Bound and redact metadata before it enters the immutable audit trail."""
    if depth >= _MAX_DEPTH:
        return "[truncated-depth]"
    if isinstance(value, dict):
        output: Dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_ITEMS:
                output["_truncated"] = True
                break
            label = str(key)[:160]
            output[label] = "[redacted]" if _SECRET_KEY_RE.search(label) else sanitize_metadata(item, depth=depth + 1)
        return output
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        output = [sanitize_metadata(item, depth=depth + 1) for item in items[:_MAX_ITEMS]]
        if len(items) > _MAX_ITEMS:
            output.append("[truncated-items]")
        return output
    return _safe_scalar(value)


def metadata_sha256(metadata: Dict[str, Any]) -> str:
    canonical = json.dumps(metadata or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def classify_action(action: str) -> tuple[str, str]:
    normalized = str(action or "").strip().lower()
    if normalized.startswith("view.") or normalized.startswith("read."):
        return "read", "info"
    if any(token in normalized for token in ("suspend", "deactivate", "retry", "requeue", "adjust", "delete", "cancel", "quarantine")):
        return "privileged_mutation", "high"
    if any(token in normalized for token in ("create", "update", "upsert", "customer.", "staff.")):
        return "mutation", "medium"
    return "system", "info"


def build_audit_payload(
    admin: Dict[str, Any],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = current_audit_context()
    safe_metadata = sanitize_metadata(metadata or {})
    category, severity = classify_action(action)
    profile = admin.get("profile") if isinstance(admin.get("profile"), dict) else {}
    actor_user_id = profile.get("auth_user_id") or profile.get("user_id") or admin.get("auth_user_id")
    target_owner_email = safe_metadata.get("owner_email") or safe_metadata.get("customer_email") if isinstance(safe_metadata, dict) else None
    return {
        "p_audit_id": make_public_id("audit"),
        "p_actor_email": admin.get("email"),
        "p_actor_role": admin.get("role"),
        "p_actor_user_id": actor_user_id,
        "p_action": str(action or "")[:180],
        "p_entity_type": str(entity_type or "")[:100],
        "p_entity_id": str(entity_id or "")[:180] or None,
        "p_target_owner_email": str(target_owner_email or "")[:320] or None,
        "p_metadata": safe_metadata,
        "p_metadata_sha256": metadata_sha256(safe_metadata if isinstance(safe_metadata, dict) else {"value": safe_metadata}),
        "p_event_category": category,
        "p_severity": severity,
        "p_request_id": context.get("request_id"),
        "p_ip_address": context.get("ip_address"),
        "p_user_agent": context.get("user_agent"),
        "p_write_origin": "api",
    }


def record_audit_event(
    admin: Dict[str, Any],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    require_durable: bool = False,
) -> Optional[Dict[str, Any]]:
    """Append an integrity-protected audit event through the database RPC.

    Existing state mutations are not rolled back here because several legacy
    mutations are separate REST calls. Callers can opt into an explicit error
    with ``require_durable`` where their endpoint is designed to handle it.
    """
    payload = build_audit_payload(admin, action, entity_type, entity_id, metadata)
    if not is_configured():
        return {"durable": False, **payload}
    try:
        row = call_rpc("append_audit_event", payload)
    except ProductionStoreError as exc:
        if require_durable:
            raise AuditWriteError("Durable audit event could not be recorded.") from exc
        return None
    if isinstance(row, list):
        return row[0] if row else None
    return row if isinstance(row, dict) else None


def redact_audit_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Keep admin responses useful without exposing raw network or secret data."""
    hidden = {"ip_address", "user_agent"}
    output = {key: value for key, value in dict(row or {}).items() if key not in hidden}
    if "metadata" in output:
        output["metadata"] = sanitize_metadata(output.get("metadata") or {})
    return output


def audit_integrity_status(*, limit: int = 2000) -> Dict[str, Any]:
    """Return the database-side integrity verification result for staff UI."""
    checked_limit = max(1, min(int(limit or 2000), 10000))
    if not is_configured():
        return {
            "available": False,
            "verified": False,
            "reason": "production_store_not_configured",
            "checked_events": 0,
        }
    try:
        row = call_rpc("audit_integrity_status", {"p_limit": checked_limit})
    except ProductionStoreError:
        return {
            "available": False,
            "verified": False,
            "reason": "audit_integrity_rpc_unavailable",
            "checked_events": 0,
        }
    if isinstance(row, list):
        row = row[0] if row else {}
    return dict(row or {}) if isinstance(row, dict) else {
        "available": False,
        "verified": False,
        "reason": "invalid_audit_integrity_response",
        "checked_events": 0,
    }
