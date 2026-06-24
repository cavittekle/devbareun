"""Privacy-safe, project-scoped activity timeline helpers.

The timeline is intentionally distinct from the global audit hash-chain. It
contains collaboration-relevant events that may be read by project viewers,
while global audit records remain a staff/owner operational control.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from ..auth_dependencies import CurrentUser, local_store_enabled
from ..production_store import ProductionStoreError, insert_row, is_configured, select_rows, uuid_like
from ..saas_ids import make_public_id
from .audit_service import metadata_sha256, sanitize_metadata
from .project_sharing_service import can_access_project_resource

PROJECT_ACTIVITY_SCHEMA_VERSION = "v1"
MAX_ACTIVITY_LIMIT = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _project_db_id(project: Dict[str, Any]) -> str | None:
    value = str(project.get("id") or project.get("project_id") or "").strip()
    return value if uuid_like(value) else None


def _actor_payload(actor: CurrentUser | None) -> Dict[str, Any]:
    if actor is None:
        return {"actor_type": "system", "actor_user_id": None, "actor_email": None}
    user_id = str(actor.id or "").strip()
    return {
        "actor_type": "user",
        "actor_user_id": user_id if uuid_like(user_id) else None,
        "actor_email": str(actor.email or "").strip().lower() or None,
    }


def record_project_activity(
    project: Dict[str, Any],
    actor: CurrentUser | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Append a project-visible event without allowing it to break core work.

    Callers normally invoke this best-effort after the primary mutation. The
    service redacts credential-like metadata and never accepts storage paths,
    signed URLs or raw payloads as a display surface.
    """
    project_id = _project_db_id(project)
    safe_metadata = sanitize_metadata(metadata or {})
    safe_metadata = dict(safe_metadata) if isinstance(safe_metadata, dict) else {"value": safe_metadata}
    for forbidden in ("storage_path", "signed_url", "signed_upload_url", "raw_payload", "content"):
        safe_metadata.pop(forbidden, None)
    if not project_id:
        return None
    payload: Dict[str, Any] = {
        "event_id": make_public_id("activity"),
        "project_id": project_id,
        "company_id": str(project.get("company_id") or "") or None,
        "action": str(action or "project.activity")[:180],
        "entity_type": str(entity_type or "project")[:100],
        "entity_id": str(entity_id or "")[:180] or None,
        "metadata": safe_metadata,
        "metadata_sha256": metadata_sha256(safe_metadata),
        "visibility": "project",
        "schema_version": PROJECT_ACTIVITY_SCHEMA_VERSION,
        "created_at": _now(),
    }
    payload.update(_actor_payload(actor))
    try:
        if is_configured():
            return insert_row("project_activity_events", payload)
        if local_store_enabled():
            from ..saas_store import insert
            return insert("project_activity_events", payload)
    except ProductionStoreError:
        return None
    return None


def _event_api(row: Dict[str, Any]) -> Dict[str, Any]:
    metadata = sanitize_metadata(row.get("metadata") or {})
    if not isinstance(metadata, dict):
        metadata = {"value": metadata}
    return {
        "event_id": row.get("event_id") or row.get("id"),
        "action": str(row.get("action") or "project.activity"),
        "entity_type": str(row.get("entity_type") or "project"),
        "entity_id": row.get("entity_id"),
        "actor": {
            "type": str(row.get("actor_type") or "user"),
            "email": row.get("actor_email"),
        },
        "metadata": metadata,
        "occurred_at": row.get("created_at"),
        "schema_version": row.get("schema_version") or PROJECT_ACTIVITY_SCHEMA_VERSION,
    }


def list_project_activity(project: Dict[str, Any], actor: CurrentUser, *, limit: int = 80) -> list[Dict[str, Any]]:
    if not can_access_project_resource(project, actor, "project_activity"):
        raise PermissionError("You do not have permission to view this project activity.")
    project_id = _project_db_id(project)
    if not project_id:
        return []
    bounded_limit = max(1, min(int(limit or 80), MAX_ACTIVITY_LIMIT))
    if is_configured():
        rows = select_rows("project_activity_events", {"project_id": project_id}, limit=bounded_limit)
    elif local_store_enabled():
        from ..saas_store import list_rows
        rows = list_rows("project_activity_events", project_id=project_id)[:bounded_limit]
    else:
        rows = []
    rows = [row for row in rows if str(row.get("visibility") or "project").lower() == "project"]
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return [_event_api(row) for row in rows[:bounded_limit]]
