from __future__ import annotations

import json
import hashlib
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException

from ..auth_dependencies import CurrentUser, local_store_enabled, normalize_user_role
from ..access_control import can_access_project_scope, can_operate_analysis_jobs, is_staff_role
from ..analysis_types import normalize_analysis_type
from ..production_store import ProductionStoreError, first_existing, first_update, insert_row, is_configured, select_rows, upsert_row, uuid_like
from ..security_runtime import production_security_enabled
from .analytics_service import build_analytics
from .project_activity_service import record_project_activity
from .project_sharing_service import can_access_project_resource, list_accessible_projects
from .analysis_provenance import build_analysis_input_manifest
from .billing_service import consume_after_success, ensure_analysis_available
from .parser_service import parse_project_files
from .premium_analysis import analyze_full_project_control_premium
from .risk_engine import generate_risk_register


JOB_STATUSES = {"queued", "running", "completed", "failed", "dead_lettered"}
JOB_MODES = {"background", "worker", "inline"}
TERMINAL_RECOVERY_STATUSES = {"failed", "dead_lettered"}
DEFAULT_ANALYSIS_JOB_MAX_ATTEMPTS = 3
MAX_ANALYSIS_JOB_MAX_ATTEMPTS = 10
DEFAULT_WORKER_STALE_AFTER_MINUTES = 45
DEFAULT_JOB_HEARTBEAT_INTERVAL_SECONDS = 60
DEFAULT_WORKER_STATUS_STALE_SECONDS = 90
_LOCAL_WORKER_HEARTBEATS: Dict[str, Dict[str, Any]] = {}


def analysis_job_max_attempts() -> int:
    """Return a bounded retry budget for newly-created durable jobs."""
    raw = os.getenv("DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS") or str(DEFAULT_ANALYSIS_JOB_MAX_ATTEMPTS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_ANALYSIS_JOB_MAX_ATTEMPTS
    return max(1, min(value, MAX_ANALYSIS_JOB_MAX_ATTEMPTS))


def analysis_job_heartbeat_interval_seconds() -> int:
    """Bound the recurring heartbeat interval so long parser calls stay visible."""
    raw = os.getenv("DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS") or str(DEFAULT_JOB_HEARTBEAT_INTERVAL_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_JOB_HEARTBEAT_INTERVAL_SECONDS
    return max(10, min(value, 600))


def analysis_worker_status_stale_seconds() -> int:
    raw = os.getenv("DEVBAREUN_ANALYSIS_WORKER_STATUS_STALE_SECONDS") or str(DEFAULT_WORKER_STATUS_STALE_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_WORKER_STATUS_STALE_SECONDS
    return max(30, min(value, 3600))


class _JobHeartbeat:
    """Refresh a running job while parser/analytics work blocks the worker loop."""

    def __init__(self, job_id: str, worker_id: str | None = None) -> None:
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval = analysis_job_heartbeat_interval_seconds()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"devbareun-job-heartbeat-{job_id}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=min(5.0, float(self.interval)))

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                heartbeat_analysis_job(self.job_id, worker_id=self.worker_id)
            except Exception:
                # A later job update will surface persistent database failures; a
                # transient heartbeat failure must not terminate parser work.
                continue




def analysis_job_mode() -> str:
    """Return how API-created analysis jobs should be executed.

    background: current FastAPI BackgroundTasks behavior.
    worker: API only queues jobs; run `python -m app.analysis_worker` separately.
    inline: execute synchronously, useful only for local debugging/tests.
    """
    value = str(os.getenv("DEVBAREUN_ANALYSIS_JOB_MODE") or "background").strip().lower()
    return value if value in JOB_MODES else "background"


def create_analysis_job(
    *,
    project_id: str,
    project: Dict[str, Any],
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    analysis_type: str = "all",
    idempotency_key: str | None = None,
) -> Dict[str, Any]:
    analysis_type = normalize_analysis_type(analysis_type)
    normalized_key = _normalize_idempotency_key(idempotency_key)
    db_project_id = _project_db_id(project, project_id)
    request_fingerprint = _analysis_request_fingerprint(db_project_id or project_id, analysis_type)
    if normalized_key:
        replay = _find_idempotent_job(user, normalized_key)
        if replay:
            if str(replay.get("request_fingerprint") or "") not in {"", request_fingerprint}:
                raise HTTPException(status_code=409, detail={"error": "idempotency_key_reused", "message": "This Idempotency-Key was already used for a different analysis request."})
            return _job_response(replay, idempotent_replay=True)
    active = _find_active_job_for_project(db_project_id, user)
    if active:
        return _job_response(active, active_job_reused=True)
    ensure_analysis_available(user, project_id)
    files = list_project_files_for_analysis(project_id, project)
    if not files:
        raise HTTPException(status_code=400, detail={"error": "no_uploaded_files", "message": "Upload project files before starting project review."})

    if not is_configured():
        if local_store_enabled():
            return _create_local_job(project_id, user, files, analysis_type, background_tasks, project, normalized_key)
        if production_security_enabled():
            raise HTTPException(status_code=503, detail={"error": "database_not_configured", "message": "Supabase PostgreSQL is required for background analysis jobs."})
        raise HTTPException(status_code=503, detail={"error": "local_store_disabled", "message": "Enable DEVBAREUN_ENABLE_LOCAL_STORE=true for local development fallback."})

    queued_manifest = build_analysis_input_manifest(files)
    payload = {
        "user_id": _user_uuid(user),
        "project_id": db_project_id,
        "owner_email": user.email,
        "analysis_type": analysis_type,
        "status": "queued",
        "progress": 0,
        "attempts": 0,
        "max_attempts": analysis_job_max_attempts(),
        "requeue_count": 0,
        "idempotency_key": normalized_key,
        "request_fingerprint": request_fingerprint,
        "billing_status": "pending",
        **_provenance_patch(queued_manifest),
        "created_at": _now(),
        "updated_at": _now(),
    }
    try:
        job = _insert_analysis_job(payload, user)
    except ProductionStoreError as exc:
        # Unique indexes introduced by v1.4.18 turn concurrent duplicate clicks
        # into a safe replay rather than parallel parser work.
        replay = _find_idempotent_job(user, normalized_key) if normalized_key else None
        active = _find_active_job_for_project(db_project_id, user)
        if replay:
            return _job_response(replay, idempotent_replay=True)
        if active:
            return _job_response(active, active_job_reused=True)
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Analysis job could not be created."}) from exc

    job_id = str(job.get("id") or job.get("job_id"))
    response = _job_response(job)
    _schedule_or_run_job(job_id=job_id, project_id=project_id, user=user, analysis_type=analysis_type, background_tasks=background_tasks)
    if analysis_job_mode() == "inline":
        current = _find_job(job_id) or {}
        response["status"] = str(current.get("status") or response["status"])
    return response


def run_analysis_job(
    *,
    job_id: str,
    project_id: str,
    user_payload: Dict[str, Any],
    analysis_type: str = "all",
    worker_id: str | None = None,
) -> None:
    """Execute one durable analysis job with periodic persistence heartbeats."""
    analysis_type = normalize_analysis_type(analysis_type)
    user = CurrentUser(**_normalize_user_payload(user_payload))
    runtime_worker_id = worker_id or _default_worker_id(prefix="analysis-runtime")
    heartbeat = _JobHeartbeat(job_id, worker_id=runtime_worker_id)
    files: List[Dict[str, Any]] = []
    try:
        _update_job(
            job_id,
            {
                "status": "running",
                "progress": 15,
                "started_at": _now(),
                "error_message": None,
                "worker_id": runtime_worker_id,
            },
        )
        heartbeat.start()
        project = _load_project_for_job(project_id)
        files = list_project_files_for_analysis(project_id, project)
        if not files:
            raise RuntimeError("No uploaded project files were found.")

        # Persist an input snapshot before parser work begins. This preserves an
        # audit record even when a materialization, checksum or security gate
        # later rejects one of the selected source files.
        pre_parse_manifest = build_analysis_input_manifest(files)
        _update_job(job_id, _provenance_patch(pre_parse_manifest))

        _update_job(job_id, {"progress": 35})
        normalized = parse_project_files(files, analysis_type=analysis_type, project=project)
        for source_file in files:
            source_file["parser_status"] = "parsed"
        # parser_service enriches each in-memory row with verified checksum and
        # screening state. Snapshot again so saved results identify the bytes
        # that actually reached the parser, not merely the initially requested
        # upload metadata.
        input_manifest = build_analysis_input_manifest(files)
        normalized["analysis_provenance"] = input_manifest
        _update_job(job_id, _provenance_patch(input_manifest))
        _update_job(job_id, {"progress": 58})
        analytics = build_analytics(normalized, project)
        analytics["analysis_provenance"] = input_manifest
        risks = generate_risk_register(normalized, analytics)
        analytics.setdefault("metrics", {})["high_risk_count"] = len([risk for risk in risks if risk.get("severity") in {"High", "Critical"}])
        premium_dashboard = analyze_full_project_control_premium(normalized, analytics, risks)
        analytics["analysis_type"] = premium_dashboard["analysis_type"]
        analytics["premium_dashboard"] = premium_dashboard
        _update_job(job_id, {"progress": 78})
        result = _save_result(user, project, project_id, job_id, normalized, analytics, risks, input_manifest=input_manifest)
        _save_risks(user, project, project_id, result, risks)
        billing = consume_after_success(user, project_id, job_id)
        _update_job(job_id, {"billing_status": _billing_status_from_result(billing)})
        _mark_files_parsed(files)
        heartbeat.stop()
        _update_job(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "completed_at": _now(),
                "locked_at": None,
                "worker_id": None,
                "terminal_reason": None,
            },
        )
        try:
            record_project_activity(
                project,
                user,
                "analysis.completed",
                "analysis_job",
                job_id,
                {"analysis_result_id": result.get("analysis_id") or result.get("id"), "risk_count": len(risks)},
            )
        except Exception:
            pass
    except Exception as exc:
        heartbeat.stop()
        _persist_file_integrity_state(files)
        if files:
            # Keep the final in-memory integrity/screening state with the failed
            # job. Operators can then identify which source blocked the run.
            _update_job(job_id, _provenance_patch(build_analysis_input_manifest(files)))
        _update_job(
            job_id,
            {
                "status": "failed",
                "progress": 100,
                "error_message": _safe_error(exc),
                "completed_at": _now(),
                "locked_at": None,
                "worker_id": None,
                "terminal_reason": "runtime_failure",
            },
        )
        try:
            record_project_activity(project, user, "analysis.failed", "analysis_job", job_id, {"terminal_reason": "runtime_failure"})
        except Exception:
            pass
    finally:
        heartbeat.stop()


def heartbeat_analysis_job(job_id: str, *, worker_id: str | None = None) -> None:
    """Persist a liveness signal without changing the current job progress."""
    patch: Dict[str, Any] = {"status": "running", "last_heartbeat_at": _now()}
    if worker_id:
        patch["worker_id"] = worker_id
    _update_job(job_id, patch)


def record_analysis_worker_heartbeat(
    *,
    worker_id: str,
    status: str = "online",
    result: Dict[str, Any] | None = None,
    error_type: str | None = None,
) -> None:
    """Upsert a secret-safe worker liveness record for operator visibility."""
    now = _now()
    metadata: Dict[str, Any] = {"analysis_job_mode": analysis_job_mode()}
    if result:
        metadata.update(
            {
                "claimed": int(result.get("claimed") or 0),
                "processed": int(result.get("processed") or 0),
                "stale_requeued": int(result.get("stale_requeued") or 0),
            }
        )
    if error_type:
        metadata["error_type"] = error_type
    payload = {
        "worker_id": worker_id,
        "status": status,
        "last_seen_at": now,
        "last_result_at": now if result or error_type else None,
        "processed_jobs": int((result or {}).get("processed") or 0),
        "claimed_jobs": int((result or {}).get("claimed") or 0),
        "metadata": metadata,
        "updated_at": now,
    }
    if is_configured():
        try:
            upsert_row("analysis_worker_heartbeats", payload, on_conflict="worker_id")
            return
        except ProductionStoreError:
            # The service remains usable before the additive v1.4.16 migration is applied.
            return
    if local_store_enabled():
        current = dict(_LOCAL_WORKER_HEARTBEATS.get(worker_id) or {})
        current.setdefault("worker_id", worker_id)
        current.setdefault("started_at", now)
        current.update({key: value for key, value in payload.items() if value is not None})
        _LOCAL_WORKER_HEARTBEATS[worker_id] = current


def analysis_operations_status() -> Dict[str, Any]:
    """Return aggregate queue and worker health data without user/job payloads."""
    jobs: List[Dict[str, Any]] = []
    workers: List[Dict[str, Any]] = []
    store = "unavailable"
    if is_configured():
        try:
            jobs = select_rows("analysis_jobs", limit=1000)
            store = "supabase"
        except ProductionStoreError:
            store = "supabase_unavailable"
        if store == "supabase":
            try:
                workers = select_rows("analysis_worker_heartbeats", limit=100)
            except ProductionStoreError:
                # Keep aggregate queue visibility during a rolling deploy where
                # web code arrives just before the additive observability migration.
                workers = []
    elif local_store_enabled():
        from ..saas_store import list_rows

        jobs = list_rows("analysis_jobs")
        workers = list(_LOCAL_WORKER_HEARTBEATS.values())
        store = "local"

    counts = {status: 0 for status in sorted(JOB_STATUSES)}
    for job in jobs:
        status = str(job.get("status") or "unknown").lower()
        if status in counts:
            counts[status] += 1
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stale_after = analysis_worker_status_stale_seconds()
    safe_workers: List[Dict[str, Any]] = []
    for row in workers:
        seen = _parse_datetime(row.get("last_seen_at"))
        age_seconds = int((now - seen).total_seconds()) if seen else None
        worker_status = str(row.get("status") or "unknown")
        healthy = worker_status == "online" and age_seconds is not None and age_seconds <= stale_after
        safe_workers.append(
            {
                "worker_id": str(row.get("worker_id") or ""),
                "status": worker_status,
                "healthy": healthy,
                "last_seen_at": row.get("last_seen_at"),
                "last_result_at": row.get("last_result_at"),
                "processed_jobs": int(row.get("processed_jobs") or 0),
                "claimed_jobs": int(row.get("claimed_jobs") or 0),
                "metadata": _coerce_json_dict(row.get("metadata")),
            }
        )
    healthy_workers = len([row for row in safe_workers if row["healthy"]])
    return {
        "store": store,
        "execution_mode": analysis_job_mode(),
        "queue": counts,
        "workers": safe_workers,
        "healthy_worker_count": healthy_workers,
        "worker_heartbeat_stale_seconds": stale_after,
        "worker_required": analysis_job_mode() == "worker",
        "worker_available": healthy_workers > 0 if analysis_job_mode() == "worker" else None,
        "generated_at": _now(),
    }


def run_worker_once(*, batch_size: int = 1, worker_id: str | None = None, stale_after_minutes: int = DEFAULT_WORKER_STALE_AFTER_MINUTES) -> Dict[str, Any]:
    """Claim and run a small batch of queued analysis jobs.

    This is intentionally table-backed and dependency-light so Railway can run it
    as a separate worker service without Redis/Celery. Set
    DEVBAREUN_ANALYSIS_JOB_MODE=worker on the web service, then run
    `python -m app.analysis_worker --loop` on the worker service.
    """
    worker_id = worker_id or _default_worker_id()
    if not is_configured() and not local_store_enabled():
        if production_security_enabled():
            raise RuntimeError("Supabase PostgreSQL is required for analysis worker mode.")
        return {"worker_id": worker_id, "processed": 0, "claimed": 0, "stale_requeued": 0, "jobs": [], "message": "No configured job store."}

    record_analysis_worker_heartbeat(worker_id=worker_id, status="online")
    stale_requeued = requeue_stale_analysis_jobs(stale_after_minutes=stale_after_minutes)
    candidates = _list_claimable_jobs(batch_size)
    processed: List[Dict[str, Any]] = []
    claimed_count = 0
    for candidate in candidates:
        claimed = _claim_job(candidate, worker_id)
        if not claimed:
            continue
        claimed_count += 1
        job_identifier = str(claimed.get("id") or claimed.get("job_id") or "")
        project_id = str(claimed.get("project_id") or claimed.get("project_public_id") or "")
        analysis_type = str(claimed.get("analysis_type") or "all")
        if not job_identifier or not project_id:
            _update_job(job_identifier, {"status": "failed", "progress": 100, "error_message": "Analysis job is missing project_id.", "completed_at": _now()})
            processed.append({"job_id": job_identifier or "unknown", "status": "failed", "error": "missing_project_id"})
            continue
        if _analysis_result_exists_for_job(job_identifier):
            _recover_persisted_result(job_identifier, claimed)
        else:
            user = _user_from_job(claimed)
            run_analysis_job(
                job_id=job_identifier,
                project_id=project_id,
                user_payload=user.payload(),
                analysis_type=analysis_type,
                worker_id=worker_id,
            )
        current = _find_job(job_identifier) or {}
        processed.append({"job_id": job_identifier, "project_id": project_id, "status": current.get("status") or "unknown"})
    result = {"worker_id": worker_id, "claimed": claimed_count, "processed": len(processed), "stale_requeued": stale_requeued, "jobs": processed}
    record_analysis_worker_heartbeat(worker_id=worker_id, status="online", result=result)
    return result


def requeue_stale_analysis_jobs(*, stale_after_minutes: int = DEFAULT_WORKER_STALE_AFTER_MINUTES) -> int:
    """Return abandoned running jobs to the queue without exceeding their budget.

    Jobs that have exhausted their configured claim attempts are moved to the
    explicit ``dead_lettered`` terminal state. This makes an operator decision
    necessary before they can run again. A stale job that already persisted an
    analysis result is completed instead of being run twice.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=max(1, int(stale_after_minutes)))
    recovered = 0
    for row in _list_running_jobs(limit=100):
        last_seen = _parse_datetime(row.get("last_heartbeat_at") or row.get("locked_at") or row.get("started_at"))
        if not last_seen or last_seen > cutoff:
            continue
        job_id = str(row.get("id") or row.get("job_id") or "")
        if not job_id:
            continue
        if _analysis_result_exists_for_job(job_id):
            _recover_persisted_result(job_id, row)
            recovered += 1
            continue
        attempts = int(row.get("attempts") or 0)
        max_attempts = max(1, int(row.get("max_attempts") or analysis_job_max_attempts()))
        requeue_count = int(row.get("requeue_count") or 0)
        if attempts >= max_attempts:
            _update_job(
                job_id,
                {
                    "status": "dead_lettered",
                    "progress": 100,
                    "error_message": "Analysis worker timed out after the maximum retry budget.",
                    "terminal_reason": "worker_timeout_max_attempts",
                    "completed_at": _now(),
                    "locked_at": None,
                    "worker_id": None,
                },
            )
        else:
            _update_job(
                job_id,
                {
                    "status": "queued",
                    "progress": 0,
                    "error_message": "Analysis worker timed out; job was returned to queue.",
                    "terminal_reason": None,
                    "requeue_count": requeue_count + 1,
                    "locked_at": None,
                    "worker_id": None,
                    "last_heartbeat_at": None,
                },
            )
        recovered += 1
    return recovered


def list_analysis_recovery_jobs(*, limit: int = 50) -> List[Dict[str, Any]]:
    """Return staff-safe failed/dead-letter job metadata without customer payloads."""
    safe_limit = max(1, min(int(limit or 50), 100))
    if is_configured():
        rows = select_rows("analysis_jobs", limit=1000)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("analysis_jobs")
    else:
        return []
    filtered = [row for row in rows if str(row.get("status") or "").lower() in TERMINAL_RECOVERY_STATUSES]
    filtered.sort(key=lambda row: str(row.get("updated_at") or row.get("completed_at") or row.get("created_at") or ""), reverse=True)
    result: List[Dict[str, Any]] = []
    for row in filtered[:safe_limit]:
        job_id = str(row.get("id") or row.get("job_id") or "")
        attempts = int(row.get("attempts") or 0)
        max_attempts = max(1, int(row.get("max_attempts") or analysis_job_max_attempts()))
        status = str(row.get("status") or "failed").lower()
        has_result = _analysis_result_exists_for_job(job_id) if job_id else False
        result.append(
            {
                "job_id": job_id,
                "project_id": str(row.get("project_id") or row.get("project_public_id") or ""),
                "status": status,
                "attempts": attempts,
                "max_attempts": max_attempts,
                "requeue_count": int(row.get("requeue_count") or 0),
                "retryable": status == "failed" and attempts < max_attempts and not has_result,
                "requires_attempt_reset": status == "dead_lettered" or attempts >= max_attempts,
                "result_already_persisted": has_result,
                "terminal_reason": row.get("terminal_reason"),
                "error_message": row.get("error_message"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "completed_at": row.get("completed_at"),
                "last_heartbeat_at": row.get("last_heartbeat_at"),
            }
        )
    return result


def requeue_analysis_job(*, job_id: str, actor: CurrentUser, reset_attempts: bool = False) -> Dict[str, Any]:
    """Staff-only manual recovery for failed/dead-letter jobs.

    The recovery path deliberately refuses jobs that already have a saved result,
    so a billing/storage tail failure cannot lead an operator to duplicate output.
    A dead-lettered job requires an explicit retry-budget reset.
    """
    if not can_operate_analysis_jobs(actor.role):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Operations permission is required for job recovery."})
    job = _find_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Analysis job was not found."})
    status = str(job.get("status") or "").lower()
    if status not in TERMINAL_RECOVERY_STATUSES:
        raise HTTPException(status_code=409, detail={"error": "job_not_recoverable", "message": "Only failed or dead-lettered jobs can be requeued."})
    if _analysis_result_exists_for_job(job_id):
        raise HTTPException(status_code=409, detail={"error": "result_already_persisted", "message": "A completed result already exists for this job; do not retry it."})
    payload = _coerce_json_dict(job.get("user_payload"))
    if not payload:
        raise HTTPException(status_code=409, detail={"error": "missing_user_payload", "message": "This legacy job cannot be safely requeued because its user context is missing."})
    attempts = int(job.get("attempts") or 0)
    max_attempts = max(1, int(job.get("max_attempts") or analysis_job_max_attempts()))
    if attempts >= max_attempts and not reset_attempts:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "attempt_budget_exhausted",
                "message": "The job is dead-lettered. Retry again with reset_attempts=true only after reviewing the failure.",
            },
        )
    patch: Dict[str, Any] = {
        "status": "queued",
        "progress": 0,
        "error_message": None,
        "terminal_reason": None,
        "retry_requested_at": _now(),
        "retry_requested_by": actor.email,
        "requeue_count": int(job.get("requeue_count") or 0) + 1,
        "locked_at": None,
        "worker_id": None,
        "last_heartbeat_at": None,
        "started_at": None,
        "completed_at": None,
    }
    if reset_attempts:
        patch["attempts"] = 0
    _update_job(job_id, patch)
    # Build the response from the requested state. A read immediately after a
    # Supabase PATCH can observe a stale replica, but the caller must receive
    # the state that was accepted for queue recovery rather than old terminal
    # metadata.
    updated = _find_job(job_id) or {}
    if str(updated.get("status") or "").lower() != "queued":
        updated = dict(job)
        updated.update(patch)
    return {
        "job_id": job_id,
        "status": "queued",
        "attempts": int(updated.get("attempts") or 0),
        "max_attempts": int(updated.get("max_attempts") or max_attempts),
        "reset_attempts": bool(reset_attempts),
        "message": "Analysis job requeued for worker recovery.",
    }


def _analysis_result_exists_for_job(job_id: str) -> bool:
    if not job_id:
        return False
    if is_configured() and uuid_like(job_id):
        try:
            return bool(select_rows("analysis_results", {"job_id": job_id}, limit=1))
        except ProductionStoreError:
            return False
    if local_store_enabled():
        from ..saas_store import list_rows

        return bool(list_rows("analysis_results", job_id=job_id))
    return False


def get_analysis_job(job_id: str, user: CurrentUser) -> Dict[str, Any]:
    job = _find_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Analysis job was not found."})
    if not _row_belongs_to_user(job, user):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can access only your own analysis job."})
    return {"job": job}


def get_latest_analysis_result(project_id: str, project: Dict[str, Any], user: CurrentUser) -> Dict[str, Any] | None:
    db_project_id = _project_db_id(project, project_id)
    rows: List[Dict[str, Any]] = []
    if is_configured() and db_project_id:
        rows = select_rows("analysis_results", {"project_id": db_project_id}, limit=100)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("analysis_results", project_id=project_id)
    # The project route has already authorized a viewer/editor/manager. Results
    # belong to a project, not exclusively to the account that started a job.
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows[0] if rows else None


def list_project_files_for_analysis(project_id: str, project: Dict[str, Any]) -> List[Dict[str, Any]]:
    db_project_id = _project_db_id(project, project_id)
    if is_configured() and db_project_id:
        rows = select_rows("uploaded_files", {"project_id": db_project_id}, limit=500)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("uploaded_files", project_id=project_id)
    else:
        rows = []
    return [
        row for row in rows
        if str(row.get("upload_status") or row.get("status") or "").lower() in {"uploaded", "metadata_recorded", "parsed", "approved", "local_metadata_only"}
        and str(row.get("security_scan_status") or "pending").lower() not in {"blocked", "failed"}
        and str(row.get("quarantine_status") or "pending_scan").lower() != "quarantined"
        and not row.get("deleted_at")
    ]


def list_user_projects(user: CurrentUser) -> List[Dict[str, Any]]:
    if is_configured():
        if is_staff_role(user.role):
            return select_rows("projects", {}, limit=500)
        return list_accessible_projects(user)
    if local_store_enabled():
        from ..saas_store import list_rows

        return list_rows("projects", owner_email=user.email)
    return []


def list_user_results(user: CurrentUser) -> List[Dict[str, Any]]:
    if is_configured():
        if is_staff_role(user.role):
            return select_rows("analysis_results", {}, limit=500)
        projects = list_accessible_projects(user)
        project_ids = {str(row.get("id") or row.get("project_id") or "") for row in projects}
        if not project_ids:
            return []
        rows = select_rows("analysis_results", {}, limit=1000)
        return [row for row in rows if str(row.get("project_id") or "") in project_ids]
    if local_store_enabled():
        from ..saas_store import list_rows

        return list_rows("analysis_results", owner_email=user.email)
    return []


def _normalize_idempotency_key(value: str | None) -> str | None:
    key = str(value or "").strip()
    if not key:
        return None
    if len(key) > 128 or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise HTTPException(status_code=400, detail={"error": "invalid_idempotency_key", "message": "Idempotency-Key must be printable ASCII and at most 128 characters."})
    return key


def _analysis_request_fingerprint(project_identifier: str, analysis_type: str) -> str:
    source = f"{project_identifier}:{analysis_type}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def _job_response(job: Dict[str, Any], *, idempotent_replay: bool = False, active_job_reused: bool = False) -> Dict[str, Any]:
    job_id = str(job.get("id") or job.get("job_id") or "")
    status = str(job.get("status") or "queued")
    response = {
        "job_id": job_id,
        "status": status,
        "execution_mode": analysis_job_mode(),
        "message": "Existing analysis job returned" if (idempotent_replay or active_job_reused) else "Analysis job created",
    }
    if idempotent_replay:
        response["idempotent_replay"] = True
    if active_job_reused:
        response["active_job_reused"] = True
    return response


def _find_idempotent_job(user: CurrentUser, idempotency_key: str | None) -> Optional[Dict[str, Any]]:
    if not idempotency_key:
        return None
    if is_configured():
        try:
            rows = select_rows("analysis_jobs", {"owner_email": user.email, "idempotency_key": idempotency_key}, limit=2)
        except ProductionStoreError:
            return None
        return rows[0] if rows else None
    if local_store_enabled():
        from ..saas_store import list_rows
        rows = list_rows("analysis_jobs", owner_email=user.email, idempotency_key=idempotency_key)
        return rows[0] if rows else None
    return None


def _find_active_job_for_project(db_project_id: str | None, user: CurrentUser) -> Optional[Dict[str, Any]]:
    if not db_project_id:
        return None
    if is_configured():
        try:
            rows = select_rows("analysis_jobs", {"project_id": db_project_id}, limit=100)
        except ProductionStoreError:
            return None
    elif local_store_enabled():
        from ..saas_store import list_rows
        rows = list_rows("analysis_jobs", project_id=db_project_id)
    else:
        return None
    for row in rows:
        if _row_belongs_to_user(row, user) and str(row.get("status") or "").lower() in {"queued", "running"}:
            return row
    return None


def _billing_status_from_result(result: Dict[str, Any]) -> str:
    mode = str(result.get("mode") or "").lower()
    if result.get("already_consumed"):
        return "consumed"
    if mode == "admin_unlimited":
        return "admin_unlimited"
    return "consumed" if result.get("consumed") else "pending"


def _recover_persisted_result(job_id: str, job: Dict[str, Any]) -> bool:
    """Reconcile billing before marking a result-bearing job complete after a crash."""
    billing_status = str(job.get("billing_status") or "").lower()
    # Jobs created before v1.4.18 have no billing state. Preserve their
    # historical behavior; only new jobs explicitly marked pending enter the
    # atomic reconciliation path.
    if billing_status != "pending":
        _update_job(job_id, {"status": "completed", "progress": 100, "completed_at": _now(), "locked_at": None, "worker_id": None, "terminal_reason": "result_recovered_after_worker_timeout"})
        return True
    try:
        user = _user_from_job(job)
        project_id = str(job.get("project_id") or job.get("project_public_id") or "")
        billing = consume_after_success(user, project_id, job_id)
        _update_job(job_id, {"status": "completed", "progress": 100, "completed_at": _now(), "locked_at": None, "worker_id": None, "billing_status": _billing_status_from_result(billing), "terminal_reason": "result_billing_reconciled"})
        return True
    except Exception as exc:
        _update_job(job_id, {"status": "failed", "progress": 100, "locked_at": None, "worker_id": None, "terminal_reason": "billing_reconciliation_required", "error_message": _safe_error(exc)})
        return False


def _create_local_job(
    project_id: str,
    user: CurrentUser,
    files: List[Dict[str, Any]],
    analysis_type: str,
    background_tasks: BackgroundTasks,
    project: Dict[str, Any],
    idempotency_key: str | None = None,
) -> Dict[str, Any]:
    from ..saas_ids import make_public_id
    from ..saas_store import insert

    job_id = make_public_id("analysis").replace("DB-ANL", "DB-JOB")
    queued_manifest = build_analysis_input_manifest(files)
    insert("analysis_jobs", {
        "id": job_id,
        "job_id": job_id,
        "project_id": project_id,
        "owner_email": user.email,
        "analysis_type": analysis_type,
        "status": "queued",
        "progress": 0,
        "attempts": 0,
        "max_attempts": analysis_job_max_attempts(),
        "requeue_count": 0,
        "idempotency_key": _normalize_idempotency_key(idempotency_key),
        "request_fingerprint": _analysis_request_fingerprint(project_id, analysis_type),
        "billing_status": "pending",
        **_provenance_patch(queued_manifest),
        "user_payload": user.payload(),
        "created_at": _now(),
    })
    response = {"job_id": job_id, "status": "queued", "execution_mode": analysis_job_mode(), "message": "Analysis job created"}
    _schedule_or_run_job(job_id=job_id, project_id=project_id, user=user, analysis_type=analysis_type, background_tasks=background_tasks)
    if analysis_job_mode() == "inline":
        current = _find_job(job_id) or {}
        response["status"] = str(current.get("status") or response["status"])
    return response


def _schedule_or_run_job(*, job_id: str, project_id: str, user: CurrentUser, analysis_type: str, background_tasks: BackgroundTasks) -> None:
    mode = analysis_job_mode()
    if mode == "worker":
        return
    if mode == "inline":
        run_analysis_job(job_id=job_id, project_id=project_id, user_payload=user.payload(), analysis_type=analysis_type)
        return
    background_tasks.add_task(run_analysis_job, job_id=job_id, project_id=project_id, user_payload=user.payload(), analysis_type=analysis_type)


def _insert_analysis_job(payload: Dict[str, Any], user: CurrentUser) -> Dict[str, Any]:
    enriched = dict(payload)
    enriched.setdefault("job_id", str(uuid4()))
    enriched.setdefault("attempts", 0)
    enriched.setdefault("max_attempts", analysis_job_max_attempts())
    enriched.setdefault("requeue_count", 0)
    enriched.setdefault("user_payload", user.payload())
    try:
        return insert_row("analysis_jobs", enriched)
    except ProductionStoreError as exc:
        # Older deployments may not have the v1.4.5 worker columns yet. Keep the
        # API able to create jobs, but the worker mode should not be enabled until
        # the v145 migration is applied.
        if any(name in str(exc) for name in ["job_id", "attempts", "max_attempts", "user_payload"]):
            return insert_row("analysis_jobs", payload)
        raise


def _load_project_for_job(project_id: str) -> Dict[str, Any]:
    if is_configured():
        project = first_existing("projects", _project_filters(project_id))
        if not project:
            raise RuntimeError("Project was not found.")
        return project
    if local_store_enabled():
        from ..saas_store import find_one

        project = find_one("projects", project_id=project_id)
        if not project:
            raise RuntimeError("Project was not found.")
        return project
    raise RuntimeError("Database is not configured.")


def _provenance_patch(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Map an analysis input manifest to durable job columns."""
    return {
        "input_manifest": manifest,
        "input_manifest_sha256": manifest.get("source_fingerprint"),
        "input_file_count": int(manifest.get("file_count") or 0),
        "provenance_schema_version": manifest.get("schema_version") or "v1",
    }


def _save_result(
    user: CurrentUser,
    project: Dict[str, Any],
    project_id: str,
    job_id: str,
    normalized: Dict[str, Any],
    analytics: Dict[str, Any],
    risks: List[Dict[str, Any]],
    *,
    input_manifest: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if is_configured():
        return insert_row("analysis_results", {
            "user_id": _user_uuid(user),
            "project_id": _project_db_id(project, project_id),
            "job_id": job_id if uuid_like(job_id) else None,
            "owner_email": user.email,
            "normalized_data": normalized,
            "dashboard_data": analytics,
            "risk_data": risks,
            "input_manifest": input_manifest or {},
            "input_manifest_sha256": (input_manifest or {}).get("source_fingerprint"),
            "input_file_count": int((input_manifest or {}).get("file_count") or 0),
            "provenance_schema_version": (input_manifest or {}).get("schema_version") or "v1",
            "confidence_score": normalized.get("confidence_score") or 0,
            "analysis_type": (normalized.get("project_info") or {}).get("analysis_type") or "all",
            "status": "completed",
            "created_at": _now(),
        })
    if local_store_enabled():
        from ..saas_ids import make_public_id
        from ..saas_store import insert

        return insert("analysis_results", {
            "id": make_public_id("analysis"),
            "analysis_id": make_public_id("analysis"),
            "project_id": project_id,
            "job_id": job_id,
            "owner_email": user.email,
            "normalized_data": normalized,
            "dashboard_data": analytics,
            "risk_data": risks,
            "input_manifest": input_manifest or {},
            "input_manifest_sha256": (input_manifest or {}).get("source_fingerprint"),
            "input_file_count": int((input_manifest or {}).get("file_count") or 0),
            "provenance_schema_version": (input_manifest or {}).get("schema_version") or "v1",
            "confidence_score": normalized.get("confidence_score") or 0,
            "analysis_type": (normalized.get("project_info") or {}).get("analysis_type") or "all",
            "status": "completed",
            "created_at": _now(),
        })
    raise RuntimeError("Database is not configured.")


def _save_risks(user: CurrentUser, project: Dict[str, Any], project_id: str, result: Dict[str, Any], risks: List[Dict[str, Any]]) -> None:
    if not is_configured():
        return
    for risk in risks:
        try:
            insert_row("risks", {
                "user_id": _user_uuid(user),
                "project_id": _project_db_id(project, project_id),
                "analysis_result_id": result.get("id") if uuid_like(str(result.get("id") or "")) else None,
                "risk_title": risk.get("risk_title") or risk.get("title") or "Project risk",
                "category": risk.get("category"),
                "severity": risk.get("severity"),
                "probability": risk.get("probability"),
                "impact": risk.get("impact"),
                "explanation": risk.get("explanation") or risk.get("description"),
                "recommended_action": risk.get("recommended_action") or risk.get("action"),
                "status": risk.get("status") or "Open",
                "created_at": _now(),
            })
        except ProductionStoreError:
            continue


def _persist_file_integrity_state(files: List[Dict[str, Any]], *, parser_status: str | None = None) -> None:
    """Persist checksum verification outcomes recorded by parser_service."""
    for row in files:
        patch: Dict[str, Any] = {"updated_at": _now()}
        if parser_status:
            patch["parser_status"] = parser_status
        for key in (
            "checksum_status", "verified_checksum", "checksum_verified_at", "checksum_error",
            "security_scan_status", "security_scan_engine", "security_scan_started_at",
            "security_scan_completed_at", "security_scan_error", "security_scan_findings",
            "quarantine_status", "quarantine_reason", "quarantined_at",
            "upload_status", "status",
        ):
            if key in row:
                patch[key] = row.get(key)
        if len(patch) <= 1:
            continue
        row_id = row.get("id")
        file_id = row.get("file_id")
        try:
            if is_configured() and row_id:
                first_update("uploaded_files", {"id": row_id}, patch)
            elif local_store_enabled() and file_id:
                from ..saas_store import update_one
                update_one("uploaded_files", "file_id", file_id, patch)
        except ProductionStoreError:
            continue


def _mark_files_parsed(files: List[Dict[str, Any]]) -> None:
    _persist_file_integrity_state(files, parser_status="parsed")


def _list_claimable_jobs(limit: int = 1) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 1), 25))
    if is_configured():
        rows = select_rows("analysis_jobs", {"status": "queued"}, limit=limit)
    elif local_store_enabled():
        from ..saas_store import list_rows

        rows = list_rows("analysis_jobs", status="queued")[:limit]
    else:
        rows = []
    rows.sort(key=lambda row: str(row.get("created_at") or ""))
    return rows[:limit]


def _list_running_jobs(limit: int = 100) -> List[Dict[str, Any]]:
    if is_configured():
        return select_rows("analysis_jobs", {"status": "running"}, limit=limit)
    if local_store_enabled():
        from ..saas_store import list_rows

        return list_rows("analysis_jobs", status="running")[:limit]
    return []


def _claim_job(job: Dict[str, Any], worker_id: str) -> Optional[Dict[str, Any]]:
    job_id = str(job.get("id") or job.get("job_id") or "")
    if not job_id:
        return None
    attempts = int(job.get("attempts") or 0)
    patch = {
        "status": "running",
        "progress": max(5, int(job.get("progress") or 0)),
        "attempts": attempts + 1,
        "worker_id": worker_id,
        "locked_at": _now(),
        "last_heartbeat_at": _now(),
        "started_at": job.get("started_at") or _now(),
        "updated_at": _now(),
    }
    if is_configured():
        try:
            if uuid_like(job_id):
                return first_update("analysis_jobs", {"id": job_id, "status": "queued"}, patch)
            return None
        except ProductionStoreError as exc:
            if any(name in str(exc) for name in ["attempts", "worker_id", "locked_at", "last_heartbeat_at"]):
                return first_update("analysis_jobs", {"id": job_id, "status": "queued"}, {"status": "running", "progress": 5, "started_at": _now(), "updated_at": _now()})
            raise
    if local_store_enabled():
        from ..saas_store import update_one

        current = _find_job(job_id)
        if not current or str(current.get("status")) != "queued":
            return None
        return update_one("analysis_jobs", "id", job_id, patch) or update_one("analysis_jobs", "job_id", job_id, patch)
    return None


def _find_job(job_id: str) -> Optional[Dict[str, Any]]:
    if is_configured():
        if uuid_like(job_id):
            return first_existing("analysis_jobs", [{"id": job_id}])
        return first_existing("analysis_jobs", [{"job_id": job_id}])
    if local_store_enabled():
        from ..saas_store import find_one

        return find_one("analysis_jobs", job_id=job_id) or find_one("analysis_jobs", id=job_id)
    return None


def _update_job(job_id: str, patch: Dict[str, Any]) -> None:
    payload = dict(patch)
    payload.setdefault("updated_at", _now())
    if payload.get("status") == "running" or "progress" in payload:
        payload.setdefault("last_heartbeat_at", _now())
    if is_configured():
        try:
            if uuid_like(job_id):
                first_update("analysis_jobs", {"id": job_id}, payload)
            else:
                first_update("analysis_jobs", {"job_id": job_id}, payload)
        except ProductionStoreError as exc:
            # Fallback for databases without v145 worker columns.
            fallback = {k: v for k, v in payload.items() if k not in {"locked_at", "worker_id", "last_heartbeat_at", "attempts", "max_attempts", "user_payload", "input_manifest", "input_manifest_sha256", "input_file_count", "provenance_schema_version"}}
            try:
                if uuid_like(job_id):
                    first_update("analysis_jobs", {"id": job_id}, fallback)
                else:
                    first_update("analysis_jobs", {"job_id": job_id}, fallback)
            except ProductionStoreError:
                return
    elif local_store_enabled():
        from ..saas_store import update_one

        update_one("analysis_jobs", "job_id", job_id, payload) or update_one("analysis_jobs", "id", job_id, payload)


def _user_from_job(job: Dict[str, Any]) -> CurrentUser:
    payload = _coerce_json_dict(job.get("user_payload"))
    if payload.get("email"):
        return CurrentUser(**_normalize_user_payload(payload))

    profile: Dict[str, Any] | None = None
    if is_configured():
        filters: List[Dict[str, Any]] = []
        if uuid_like(str(job.get("user_id") or "")):
            filters.append({"id": job.get("user_id")})
            filters.append({"auth_user_id": job.get("user_id")})
        if job.get("owner_email"):
            filters.append({"email": job.get("owner_email")})
        try:
            profile = first_existing("users_profile", filters) if filters else None
        except ProductionStoreError:
            profile = None
    email = str((profile or {}).get("email") or job.get("owner_email") or "worker@devbareun.local")
    role = normalize_user_role((profile or {}).get("role"), bool((profile or {}).get("is_admin")))
    return CurrentUser(
        id=str((profile or {}).get("id") or job.get("user_id") or email),
        auth_user_id=str((profile or {}).get("auth_user_id") or job.get("user_id") or email),
        email=email,
        full_name=(profile or {}).get("full_name"),
        role=role,
        status=str((profile or {}).get("status") or "active"),
        company_id=str((profile or {}).get("company_id") or "") or None,
        plan=str((profile or {}).get("plan") or "free"),
        is_admin=bool(role == "owner"),
    )


def _normalize_user_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(payload.get("id") or payload.get("auth_user_id") or payload.get("email") or "worker@devbareun.local"),
        "auth_user_id": str(payload.get("auth_user_id") or payload.get("id") or payload.get("email") or "worker@devbareun.local"),
        "email": str(payload.get("email") or "worker@devbareun.local"),
        "full_name": payload.get("full_name"),
        "role": normalize_user_role(str(payload.get("role") or "customer"), bool(payload.get("is_admin"))),
        "status": str(payload.get("status") or "active"),
        "company_id": payload.get("company_id"),
        "plan": str(payload.get("plan") or "free"),
        "is_admin": bool(payload.get("is_admin")),
    }


def _project_db_id(project: Dict[str, Any], requested_project_id: str) -> str | None:
    if uuid_like(str(project.get("id") or "")):
        return str(project.get("id"))
    if uuid_like(str(requested_project_id or "")):
        return str(requested_project_id)
    return None


def _user_uuid(user: CurrentUser) -> str | None:
    if uuid_like(user.id):
        return user.id
    if uuid_like(user.auth_user_id):
        return user.auth_user_id
    return None


def _project_filters(project_id: str) -> List[Dict[str, Any]]:
    filters: List[Dict[str, Any]] = []
    if uuid_like(project_id):
        filters.append({"id": project_id})
    filters.append({"project_id": project_id})
    return filters


def _row_belongs_to_user(row: Dict[str, Any], user: CurrentUser) -> bool:
    # Job and result access follows the projects capability; finance/support
    # must not receive cross-tenant analytical data just because they are staff.
    if is_staff_role(user.role):
        return can_access_project_scope(user.role, "projects")
    values = {
        str(row.get("user_id") or "").lower(),
        str(row.get("owner_email") or "").lower(),
        str(row.get("uploaded_by_user_id") or "").lower(),
    }
    candidates = {str(user.id).lower(), str(user.auth_user_id).lower(), str(user.email).lower()}
    return bool(values.intersection(candidates))


def _coerce_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_worker_id(*, prefix: str = "analysis-worker") -> str:
    host = os.getenv("RAILWAY_REPLICA_ID") or os.getenv("HOSTNAME") or "local"
    return f"{prefix}:{host}:{os.getpid()}"


def _safe_error(exc: Exception) -> str:
    if production_security_enabled():
        return "Analysis job failed. Please review uploaded files and try again."
    return f"analysis_job_failed:{exc.__class__.__name__}"
