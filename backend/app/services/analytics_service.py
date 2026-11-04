from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

# Findings at these severities become entries in the project risk register.
RISK_SEVERITY = {"critical": "Critical", "warning": "High", "high": "High", "medium": "Medium"}


def build_analytics(normalized: Dict[str, Any], project: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Dashboard metrics for a saved delay analysis.

    Every value comes from the delay engine result in ``normalized`` (see
    ``parser_service.normalize_delay_result``). Nothing is estimated here:
    a value the engine could not calculate stays ``None``.
    """
    project = project or {}
    delay = normalized.get("delay_analysis") or {}
    kpis = delay.get("kpis") or {}
    info = normalized.get("project_info") or {}
    delayed = int(kpis.get("activities_delayed") or 0)
    return {
        "project": {
            "id": project.get("id") or project.get("project_id") or info.get("project_id"),
            "name": info.get("project_name") or project.get("project_name") or "DevBareun Project",
            "location": info.get("location") or project.get("location"),
            "currency": info.get("currency") or project.get("currency"),
            "review_date": kpis.get("data_date") or date.today().isoformat(),
        },
        "metrics": {
            "planned_progress": kpis.get("planned_progress_pct"),
            "actual_progress": kpis.get("actual_progress_pct"),
            "schedule_variance": kpis.get("progress_gap_pct"),
            "spi": kpis.get("spi"),
            "spi_t": kpis.get("spi_t"),
            "delay_days": kpis.get("schedule_delay_days") or 0,
            "forecast_delay_days": kpis.get("forecast_delay_days"),
            "forecast_completion": kpis.get("forecast_finish"),
            "planned_finish": kpis.get("planned_finish"),
            "data_date": kpis.get("data_date"),
            "delay_status": kpis.get("status"),
            "activities_total": kpis.get("activities_total"),
            "activities_critical": kpis.get("activities_critical"),
            "delayed_activity_count": delayed,
            "high_risk_count": 0,
        },
        "cost_overview": [],
        "schedule_performance": _schedule_performance(normalized, delay, kpis),
        "document_control": normalized.get("document_control") or {},
        "warnings": list(normalized.get("warnings") or []),
        "confidence_score": normalized.get("confidence_score") or 0,
        "calculated_at": datetime.utcnow().isoformat(),
    }


def build_risk_register(delay: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn the delay findings that need attention into risk register rows."""
    risks: List[Dict[str, Any]] = []
    for finding in delay.get("findings") or []:
        severity = RISK_SEVERITY.get(str(finding.get("severity") or "").lower())
        if not severity or not finding.get("en"):
            continue
        risks.append({
            "risk_title": _title(finding.get("code")),
            "category": "Schedule delay",
            "severity": severity,
            "probability": None,
            "impact": finding.get("en"),
            "explanation": finding.get("en"),
            "explanation_az": finding.get("az"),
            # Actions are listed in the report's own section; a finding is not
            # tied to one action, so none is guessed here.
            "recommended_action": None,
            "status": "Open",
            "source_code": finding.get("code"),
        })
    order = {"Critical": 3, "High": 2, "Medium": 1}
    risks.sort(key=lambda item: order.get(item["severity"], 0), reverse=True)
    return risks


def _title(code: Any) -> str:
    text = str(code or "delay_finding").replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _schedule_performance(normalized: Dict[str, Any], delay: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    planned = kpis.get("planned_progress_pct")
    actual = kpis.get("actual_progress_pct")
    return {
        "planned_progress": planned or 0,
        "actual_progress": actual or 0,
        "variance": kpis.get("progress_gap_pct") or 0,
        "delay_days": int(kpis.get("schedule_delay_days") or 0),
        "stages": _wbs_stages(delay.get("wbs") or []),
        "milestones": normalized.get("milestones") or [],
    }


def _wbs_stages(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    stages: List[Dict[str, Any]] = []
    for row in rows:
        variance = row.get("finish_variance_days") or 0
        actual = row.get("actual_pct") or 0
        if actual >= 100:
            status = "Completed"
        elif variance > 0:
            status = "Delayed"
        elif actual > 0:
            status = "In Progress"
        else:
            status = "Not Started"
        stages.append({
            "name": row.get("wbs"),
            "progress": actual,
            "planned_progress": row.get("planned_pct"),
            "status": status,
            "finish_variance_days": variance,
        })
    return stages
