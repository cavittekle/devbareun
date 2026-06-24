"""Staff-safe operational health aggregation for DevBareun services.

This module deliberately exposes counts, lifecycle state and incident codes only.
It never returns job payloads, customer data, webhook configuration or secrets.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from ..security_runtime import runtime_readiness_report
from ..telemetry import error_telemetry_status
from .analysis_job_service import analysis_operations_status
from .audit_archive_service import audit_archive_operations_status


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _safe_dict(callback: Callable[[], Dict[str, Any]], fallback_reason: str) -> Dict[str, Any]:
    try:
        value = callback()
        return dict(value or {}) if isinstance(value, dict) else {"available": False, "reason": fallback_reason}
    except Exception:
        # The health surface must remain available even when a dependency has
        # failed. Never return exception text because it may contain provider
        # metadata or implementation details.
        return {"available": False, "reason": fallback_reason}


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except Exception:
        return 0


def _incident(component: str, code: str, severity: str, message: str) -> Dict[str, str]:
    return {
        "component": component,
        "code": code,
        "severity": severity,
        "message": message,
    }


def _component(name: str, status: str, summary: Dict[str, Any], incidents: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "incident_codes": [item["code"] for item in incidents],
    }


def _runtime_component(report: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    incidents: List[Dict[str, str]] = []
    ready = report.get("ready") is True
    errors = report.get("errors") if isinstance(report.get("errors"), list) else []
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    if not ready:
        incidents.append(_incident("runtime", "runtime_not_ready", "critical", "Runtime readiness has blocking configuration errors."))
    elif warnings:
        incidents.append(_incident("runtime", "runtime_warning", "warning", "Runtime readiness has non-blocking warnings."))
    status = "healthy" if ready and not warnings else ("unavailable" if not ready else "degraded")
    summary = {
        "ready": ready,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "environment": str((report.get("readiness") or {}).get("environment") or "unknown"),
    }
    return _component("runtime", status, summary, incidents), incidents


def _analysis_component(payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    incidents: List[Dict[str, str]] = []
    queue = dict(payload.get("queue") or {}) if isinstance(payload.get("queue"), dict) else {}
    store = str(payload.get("store") or "unavailable")
    required = payload.get("worker_required") is True
    available = payload.get("worker_available")
    failed = _count(queue.get("failed"))
    dead_lettered = _count(queue.get("dead_lettered"))

    status = "healthy"
    if store not in {"supabase", "local"}:
        status = "unavailable"
        incidents.append(_incident("analysis", "analysis_store_unavailable", "critical", "Analysis queue storage is unavailable."))
    elif required and available is not True:
        status = "degraded"
        incidents.append(_incident("analysis", "analysis_worker_unavailable", "critical", "Analysis worker heartbeat is unavailable or stale."))
    if dead_lettered:
        status = "degraded" if status == "healthy" else status
        incidents.append(_incident("analysis", "analysis_dead_lettered_jobs", "warning", "Analysis jobs require reviewed recovery."))
    if failed:
        status = "degraded" if status == "healthy" else status
        incidents.append(_incident("analysis", "analysis_failed_jobs", "warning", "Analysis jobs have failed and require review."))

    summary = {
        "store": store,
        "execution_mode": str(payload.get("execution_mode") or "unknown"),
        "worker_required": required,
        "worker_available": available if required else None,
        "healthy_worker_count": _count(payload.get("healthy_worker_count")),
        "queued": _count(queue.get("queued")),
        "running": _count(queue.get("running")),
        "failed": failed,
        "dead_lettered": dead_lettered,
    }
    return _component("analysis", status, summary, incidents), incidents


def _archive_component(payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    incidents: List[Dict[str, str]] = []
    mode = str(payload.get("mode") or "disabled")
    available = payload.get("available") is not False
    delivery_ready = payload.get("delivery_ready") is True
    workers = payload.get("workers") if isinstance(payload.get("workers"), list) else []
    healthy_workers = sum(1 for worker in workers if isinstance(worker, dict) and worker.get("healthy") is True)
    dead_lettered = _count(payload.get("dead_lettered"))

    status = "healthy"
    if mode == "disabled":
        status = "disabled"
    elif not available:
        status = "unavailable"
        incidents.append(_incident("audit_archive", "audit_archive_store_unavailable", "critical", "Audit archive queue storage is unavailable."))
    elif not delivery_ready:
        status = "degraded"
        incidents.append(_incident("audit_archive", "audit_archive_delivery_not_ready", "critical", "Audit archive delivery is not configured or ready."))
    elif healthy_workers < 1:
        status = "degraded"
        incidents.append(_incident("audit_archive", "audit_archive_worker_unavailable", "critical", "Audit archive worker heartbeat is unavailable or stale."))
    if dead_lettered:
        status = "degraded" if status in {"healthy", "disabled"} else status
        incidents.append(_incident("audit_archive", "audit_archive_dead_lettered", "warning", "Audit archive deliveries require owner review."))

    summary = {
        "mode": mode,
        "available": available,
        "delivery_ready": delivery_ready if mode != "disabled" else None,
        "healthy_worker_count": healthy_workers if mode != "disabled" else 0,
        "pending": _count(payload.get("pending")),
        "retry": _count(payload.get("retry")),
        "delivering": _count(payload.get("delivering")),
        "dead_lettered": dead_lettered,
    }
    return _component("audit_archive", status, summary, incidents), incidents



def _telemetry_component(payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    incidents: List[Dict[str, str]] = []
    mode = str(payload.get("mode") or "log")
    required = payload.get("required") is True
    external = payload.get("external_configured") is True
    status = "healthy"
    if mode == "disabled":
        status = "unavailable" if required else "disabled"
        if required:
            incidents.append(_incident("telemetry", "error_telemetry_required_unavailable", "critical", "Required external error telemetry is disabled or unavailable."))
    elif mode == "sentry" and not external:
        status = "unavailable" if required else "degraded"
        incidents.append(_incident("telemetry", "error_telemetry_not_configured", "critical" if required else "warning", "External error telemetry is not configured or its SDK is unavailable."))
    summary = {
        "mode": mode,
        "required": required,
        "external_configured": external if mode == "sentry" else None,
        "structured_logging": str(payload.get("structured_logging") or "enabled"),
        "request_logs": str(payload.get("request_logs") or "unknown"),
    }
    return _component("telemetry", status, summary, incidents), incidents


def _overall_status(components: List[Dict[str, Any]]) -> str:
    statuses = {str(component.get("status") or "unknown") for component in components}
    if "unavailable" in statuses:
        return "unavailable"
    if "degraded" in statuses:
        return "degraded"
    if statuses and statuses <= {"healthy", "disabled"}:
        return "healthy"
    return "unknown"


def operations_health_status() -> Dict[str, Any]:
    """Return a privacy-safe, capability-gated operational health summary."""
    readiness = _safe_dict(runtime_readiness_report, "runtime_readiness_unavailable")
    analysis = _safe_dict(analysis_operations_status, "analysis_operations_unavailable")
    archive = _safe_dict(audit_archive_operations_status, "audit_archive_operations_unavailable")
    telemetry = _safe_dict(error_telemetry_status, "error_telemetry_unavailable")

    runtime_component, runtime_incidents = _runtime_component(readiness)
    analysis_component, analysis_incidents = _analysis_component(analysis)
    archive_component, archive_incidents = _archive_component(archive)
    telemetry_component, telemetry_incidents = _telemetry_component(telemetry)
    components = [runtime_component, analysis_component, archive_component, telemetry_component]
    incidents = runtime_incidents + analysis_incidents + archive_incidents + telemetry_incidents

    return {
        "status": _overall_status(components),
        "generated_at": _utc_now(),
        "components": components,
        "incidents": incidents,
        "action_required": bool(incidents),
        "scope": "staff_safe",
    }
