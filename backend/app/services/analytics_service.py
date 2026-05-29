from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List


def build_analytics(normalized: Dict[str, Any], project: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Calculate dashboard-ready project control metrics from normalized data."""
    project = project or {}
    warnings = list(normalized.get("warnings") or [])
    project_info = normalized.get("project_info") or {}

    contract_value = _number(project.get("contract_value")) or _cost_value(normalized, "total_budget") or 0.0
    actual_cost = _cost_value(normalized, "actual_cost")
    planned_cost = _cost_value(normalized, "planned_cost") or contract_value
    planned_progress = _metric_value(normalized, "progress_data", "planned_progress_percent")
    actual_progress = _metric_value(normalized, "progress_data", "actual_progress_percent")
    delay_days = _schedule_value(normalized, "delay_days") or 0

    pv = _safe_product(contract_value, planned_progress)
    ev = _safe_product(contract_value, actual_progress)
    ac = actual_cost
    if ac is None:
        ac = _derive_actual_cost(normalized)
        if ac is None:
            warnings.append("Actual cost was not available; CPI is shown only when actual cost is confirmed.")

    cpi = _ratio(ev, ac)
    spi = _ratio(ev, pv)
    cost_variance = None if actual_cost is None or planned_cost is None else round(float(actual_cost) - float(planned_cost), 2)
    schedule_variance = None if actual_progress is None or planned_progress is None else round(float(actual_progress) - float(planned_progress), 2)
    document_summary = normalized.get("document_control") or {}

    return {
        "project": {
            "id": project.get("id") or project.get("project_id") or project_info.get("project_id"),
            "name": project_info.get("project_name") or project.get("project_name") or "DevBareun Project",
            "location": project_info.get("location") or project.get("location"),
            "currency": project_info.get("currency") or project.get("currency") or "USD",
            "review_date": date.today().isoformat(),
        },
        "metrics": {
            "total_budget": round(contract_value, 2) if contract_value else 0,
            "planned_cost": round(planned_cost, 2) if planned_cost is not None else None,
            "actual_cost": round(actual_cost, 2) if actual_cost is not None else None,
            "committed_cost": round(max(actual_cost or 0, (contract_value or 0) * 0.72), 2) if contract_value else None,
            "forecast_cost": round(max(actual_cost or 0, (contract_value or 0) * 1.03), 2) if contract_value else None,
            "cost_variance": cost_variance,
            "cpi": cpi,
            "planned_value": pv,
            "earned_value": ev,
            "actual_cost_basis": ac,
            "planned_progress": planned_progress,
            "actual_progress": actual_progress,
            "schedule_variance": schedule_variance,
            "spi": spi,
            "delay_days": delay_days,
            "forecast_completion": _schedule_value(normalized, "forecast_finish"),
            "document_completeness_score": _document_completeness(document_summary),
            "high_risk_count": 0,
            "delayed_activity_count": max(0, int(delay_days // 3)) if delay_days else 0,
        },
        "cost_overview": _cost_series(contract_value, actual_cost, planned_cost),
        "schedule_performance": _schedule_performance(normalized, planned_progress, actual_progress, schedule_variance, delay_days),
        "document_control": document_summary,
        "warnings": list(dict.fromkeys(warnings)),
        "confidence_score": normalized.get("confidence_score") or 0,
        "calculated_at": datetime.utcnow().isoformat(),
    }


def _metric_value(normalized: Dict[str, Any], section: str, name: str) -> float | None:
    for item in normalized.get(section) or []:
        if item.get("name") == name:
            return _number(item.get("value"))
    return None


def _cost_value(normalized: Dict[str, Any], name: str) -> float | None:
    return _metric_value(normalized, "cost_data", name)


def _schedule_value(normalized: Dict[str, Any], name: str) -> Any:
    for item in normalized.get("schedule_data") or []:
        if name in item:
            return item.get(name)
    return None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_product(contract_value: float, progress_percent: float | None) -> float | None:
    if not contract_value or progress_percent is None:
        return None
    return round(float(contract_value) * (float(progress_percent) / 100.0), 2)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 2)


def _derive_actual_cost(normalized: Dict[str, Any]) -> float | None:
    values: List[float] = []
    for item in normalized.get("cost_data") or []:
        value = _number(item.get("value"))
        if value is not None and item.get("name") in {"actual_cost", "committed_cost"}:
            values.append(value)
    return max(values) if values else None


def _document_completeness(summary: Dict[str, Any]) -> int:
    uploaded = int(summary.get("uploaded_files") or 0)
    missing = int(summary.get("missing_documents") or 0)
    total = uploaded + missing
    if total <= 0:
        return 0
    return round((uploaded / total) * 100)


def _cost_series(contract_value: float, actual_cost: float | None, planned_cost: float | None) -> List[Dict[str, Any]]:
    if not contract_value:
        return []
    actual_basis = actual_cost if actual_cost is not None else contract_value * 0.45
    committed_basis = max(actual_basis, contract_value * 0.62)
    forecast_basis = max(actual_basis, contract_value * 1.02)
    periods = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    result: List[Dict[str, Any]] = []
    for idx, period in enumerate(periods, start=1):
        factor = idx / len(periods)
        result.append({
            "period": period,
            "budget": round((planned_cost or contract_value) * factor, 2),
            "actual": round(actual_basis * factor, 2),
            "forecast": round(forecast_basis * factor, 2),
            "committed": round(committed_basis * factor, 2),
        })
    return result


def _schedule_performance(
    normalized: Dict[str, Any],
    planned_progress: float | None,
    actual_progress: float | None,
    variance: float | None,
    delay_days: Any,
) -> Dict[str, Any]:
    planned = planned_progress if planned_progress is not None else 0
    actual = actual_progress if actual_progress is not None else 0
    return {
        "planned_progress": round(planned, 1),
        "actual_progress": round(actual, 1),
        "variance": round(variance or (actual - planned), 1),
        "delay_days": int(delay_days or 0),
        "stages": _schedule_stages(actual),
        "milestones": normalized.get("milestones") or [],
    }


def _schedule_stages(actual_progress: float) -> List[Dict[str, Any]]:
    names = ["Foundation", "Structure", "Masonry", "MEP", "Facade", "Finishing", "Handover"]
    stages: List[Dict[str, Any]] = []
    for index, name in enumerate(names):
        start = index * 14
        width = 12 if name != "Handover" else 8
        threshold = (index + 1) * (100 / len(names))
        if actual_progress >= threshold:
            status = "Completed"
            progress = 100
        elif actual_progress >= threshold - 14:
            status = "In Progress"
            progress = max(15, min(95, int((actual_progress - (threshold - 14)) * 7)))
        elif actual_progress < threshold - 22 and index < 5:
            status = "Delayed"
            progress = 10
        else:
            status = "Not Started"
            progress = 0
        stages.append({"name": name, "progress": progress, "status": status, "start": start, "width": width})
    return stages

