"""Durable external archive delivery for integrity-protected audit events.

The database trigger in v1.4.25 snapshots every v1 audit event into an outbox
in the same transaction that writes the append-only chain. A standalone worker
may then deliver the immutable snapshot to a configured HTTPS webhook. This is
an outbox/retry mechanism, not a claim that the receiving system is immutable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..production_store import ProductionStoreError, call_rpc, is_configured, select_rows, upsert_row

ARCHIVE_MODES = {"disabled", "webhook"}
DEFAULT_ARCHIVE_MAX_ATTEMPTS = 8
DEFAULT_ARCHIVE_BATCH_SIZE = 25
DEFAULT_ARCHIVE_LEASE_SECONDS = 90
DEFAULT_ARCHIVE_TIMEOUT_SECONDS = 10
DEFAULT_ARCHIVE_HEARTBEAT_STALE_SECONDS = 90


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name) or str(default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def audit_archive_mode() -> str:
    value = str(os.getenv("DEVBAREUN_AUDIT_ARCHIVE_MODE") or "disabled").strip().lower()
    return value if value in ARCHIVE_MODES else "disabled"


def audit_archive_max_attempts() -> int:
    return _bounded_int("DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS", DEFAULT_ARCHIVE_MAX_ATTEMPTS, 1, 20)


def audit_archive_batch_size() -> int:
    return _bounded_int("DEVBAREUN_AUDIT_ARCHIVE_BATCH_SIZE", DEFAULT_ARCHIVE_BATCH_SIZE, 1, 100)


def audit_archive_lease_seconds() -> int:
    return _bounded_int("DEVBAREUN_AUDIT_ARCHIVE_LEASE_SECONDS", DEFAULT_ARCHIVE_LEASE_SECONDS, 30, 900)


def audit_archive_timeout_seconds() -> int:
    return _bounded_int("DEVBAREUN_AUDIT_ARCHIVE_TIMEOUT_SECONDS", DEFAULT_ARCHIVE_TIMEOUT_SECONDS, 2, 30)


def audit_archive_worker_stale_seconds() -> int:
    return _bounded_int(
        "DEVBAREUN_AUDIT_ARCHIVE_WORKER_STATUS_STALE_SECONDS",
        DEFAULT_ARCHIVE_HEARTBEAT_STALE_SECONDS,
        30,
        900,
    )


def _webhook_url() -> str:
    return str(os.getenv("DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL") or "").strip()


def _webhook_secret() -> str:
    return str(os.getenv("DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET") or "")


def audit_archive_delivery_ready() -> bool:
    return audit_archive_mode() == "webhook" and _webhook_url().startswith("https://") and bool(_webhook_secret())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_worker_id() -> str:
    return f"audit-archive-{socket.gethostname()}-{os.getpid()}"


def _safe_error(exc: Exception) -> str:
    text = str(exc or exc.__class__.__name__).replace("\n", " ").replace("\r", " ").strip()
    return text[:1200] or exc.__class__.__name__


def _normalize_rpc_row(value: Any) -> Dict[str, Any]:
    if isinstance(value, list):
        value = value[0] if value else {}
    return dict(value or {}) if isinstance(value, dict) else {}


def _delivery_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return the exact privacy-safe snapshot stored by the database trigger."""
    stored = row.get("payload")
    payload = dict(stored or {}) if isinstance(stored, dict) else {}
    return {
        "schema": "devbareun.audit-archive.v1",
        "archive_id": row.get("archive_id"),
        "audit_id": row.get("audit_id"),
        "integrity_version": row.get("integrity_version"),
        "event_hash": row.get("event_hash"),
        "previous_event_hash": row.get("previous_event_hash"),
        "payload_sha256": row.get("payload_sha256"),
        "created_at": row.get("created_at"),
        "event": payload,
    }


def _post_webhook(payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    secret = _webhook_secret().encode("utf-8")
    signature = hmac.new(secret, timestamp.encode("utf-8") + b"." + body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        _webhook_url(),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DevBareun-AuditArchive/1.4.26",
            "X-DevBareun-Audit-Signature": f"v1={signature}",
            "X-DevBareun-Audit-Timestamp": timestamp,
            "X-DevBareun-Audit-Event-ID": str(payload.get("audit_id") or ""),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=audit_archive_timeout_seconds()) as response:
            # Do not trust or persist arbitrary response content. A bounded
            # receipt lets operators correlate delivery without storing secrets.
            receipt = response.headers.get("X-Request-ID") or response.headers.get("X-Archive-Receipt") or ""
            return str(receipt)[:240]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"archive_webhook_http_{exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"archive_webhook_transport_{exc.reason}") from exc


def record_audit_archive_worker_heartbeat(
    *,
    worker_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_type: Optional[str] = None,
) -> None:
    """Persist liveness without exposing webhook configuration or payload data."""
    if not is_configured():
        return
    processed = int((result or {}).get("delivered", 0) or 0)
    claimed = int((result or {}).get("claimed", 0) or 0)
    payload = {
        "worker_id": str(worker_id)[:180],
        "status": str(status)[:40],
        "last_seen_at": _utc_now(),
        "last_result_at": _utc_now() if result is not None else None,
        "processed_events": max(0, processed),
        "claimed_events": max(0, claimed),
        "metadata": {
            "mode": audit_archive_mode(),
            "delivery_ready": audit_archive_delivery_ready(),
            "error_type": str(error_type or "")[:160] or None,
        },
        "updated_at": _utc_now(),
    }
    try:
        upsert_row("audit_archive_worker_heartbeats", payload, on_conflict="worker_id")
    except ProductionStoreError:
        # Liveness telemetry must never stop the delivery worker.
        return


def _record_delivery(row: Dict[str, Any], receipt: str) -> None:
    result = call_rpc(
        "record_audit_archive_delivery",
        {
            "p_archive_id": row.get("archive_id"),
            "p_lease_token": row.get("lease_token"),
            "p_receipt": receipt or None,
        },
    )
    if not _normalize_rpc_row(result):
        raise RuntimeError("audit_archive_delivery_ack_missing")


def _retry_delay_seconds(attempts: int) -> int:
    # Bounded exponential backoff: 30, 60, 120 ... max 30 minutes.
    return min(1800, 30 * (2 ** max(0, min(int(attempts or 1) - 1, 6))))


def _record_failure(row: Dict[str, Any], exc: Exception) -> Dict[str, Any]:
    result = call_rpc(
        "record_audit_archive_failure",
        {
            "p_archive_id": row.get("archive_id"),
            "p_lease_token": row.get("lease_token"),
            "p_error": _safe_error(exc),
            "p_retry_after_seconds": _retry_delay_seconds(int(row.get("attempts") or 1)),
            "p_max_attempts": audit_archive_max_attempts(),
        },
    )
    return _normalize_rpc_row(result)


def drain_audit_archive_once(*, worker_id: Optional[str] = None, batch_size: Optional[int] = None) -> Dict[str, Any]:
    """Claim and deliver a bounded batch of immutable audit snapshots."""
    worker_id = str(worker_id or _default_worker_id())[:180]
    result: Dict[str, Any] = {
        "worker_id": worker_id,
        "mode": audit_archive_mode(),
        "delivery_ready": audit_archive_delivery_ready(),
        "claimed": 0,
        "delivered": 0,
        "retried": 0,
        "dead_lettered": 0,
        "skipped": False,
    }
    if not is_configured():
        result.update({"skipped": True, "reason": "production_store_not_configured"})
        return result
    if audit_archive_mode() == "disabled":
        result.update({"skipped": True, "reason": "audit_archive_disabled"})
        record_audit_archive_worker_heartbeat(worker_id=worker_id, status="disabled", result=result)
        return result
    if not audit_archive_delivery_ready():
        result.update({"skipped": True, "reason": "audit_archive_webhook_not_configured"})
        record_audit_archive_worker_heartbeat(worker_id=worker_id, status="misconfigured", result=result)
        return result

    claimed = call_rpc(
        "claim_audit_archive_outbox",
        {
            "p_worker_id": worker_id,
            "p_limit": int(batch_size or audit_archive_batch_size()),
            "p_lease_seconds": audit_archive_lease_seconds(),
        },
    )
    rows = claimed if isinstance(claimed, list) else []
    result["claimed"] = len(rows)
    for raw_row in rows:
        row = dict(raw_row or {})
        try:
            receipt = _post_webhook(_delivery_payload(row))
            _record_delivery(row, receipt)
            result["delivered"] += 1
        except Exception as exc:
            outcome = _record_failure(row, exc)
            if str(outcome.get("status") or "") == "dead_lettered":
                result["dead_lettered"] += 1
            else:
                result["retried"] += 1
    record_audit_archive_worker_heartbeat(worker_id=worker_id, status="online", result=result)
    return result


def _worker_is_healthy(last_seen_at: Any) -> bool:
    raw = str(last_seen_at or "").strip()
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds() <= audit_archive_worker_stale_seconds()


def audit_archive_operations_status(*, limit: int = 100) -> Dict[str, Any]:
    """Staff-safe archive queue state. Never returns webhook URL, secret or event payload."""
    status: Dict[str, Any] = {
        "mode": audit_archive_mode(),
        "delivery_ready": audit_archive_delivery_ready(),
        "available": is_configured(),
        "workers": [],
    }
    if not is_configured():
        status["reason"] = "production_store_not_configured"
        return status
    try:
        rpc = _normalize_rpc_row(call_rpc("audit_archive_status", {"p_limit": max(1, min(int(limit or 100), 1000))}))
        status.update(rpc)
        workers = select_rows("audit_archive_worker_heartbeats", limit=100)
        status["workers"] = [
            {
                "worker_id": row.get("worker_id"),
                "status": row.get("status"),
                "last_seen_at": row.get("last_seen_at"),
                "last_result_at": row.get("last_result_at"),
                "processed_events": row.get("processed_events"),
                "claimed_events": row.get("claimed_events"),
                "healthy": _worker_is_healthy(row.get("last_seen_at")),
            }
            for row in workers
        ]
    except ProductionStoreError:
        status.update({"available": False, "reason": "audit_archive_rpc_unavailable"})
    return status


def retry_audit_archive_item(*, archive_id: str, actor: Any, reset_attempts: bool = False) -> Dict[str, Any]:
    """Explicit owner recovery for a reviewed archive dead-letter event."""
    if not is_configured():
        raise RuntimeError("production_store_not_configured")
    if isinstance(actor, dict):
        actor_email = str(actor.get("email") or "")
    else:
        actor_email = str(getattr(actor, "email", None) or "")
    row = call_rpc(
        "retry_audit_archive_item",
        {
            "p_archive_id": str(archive_id or "")[:180],
            "p_reset_attempts": bool(reset_attempts),
            "p_requested_by": actor_email[:320] or None,
        },
    )
    output = _normalize_rpc_row(row)
    if not output:
        raise RuntimeError("audit_archive_retry_not_applied")
    return output
