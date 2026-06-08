from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List


EMPTY_STATE_TEXT = "Upload project files and run analysis to generate dashboard."


def build_executive_dashboard(
    *,
    project: Dict[str, Any] | None = None,
    analysis_result: Dict[str, Any] | None = None,
    projects: Iterable[Dict[str, Any]] | None = None,
    reports: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    project = project or {}
    result = analysis_result or {}
    dashboard_data = result.get("dashboard_data") or {}
    risk_data = result.get("risk_data") or []
    if isinstance(risk_data, dict):
        risk_data = risk_data.get("risks") or risk_data.get("top_risks") or []
    metrics = dashboard_data.get("metrics") or {}
    schedule = dashboard_data.get("schedule_performance") or {}
    document_control = dashboard_data.get("document_control") or {}
    active_projects = len(list(projects or [])) or (1 if project else 0)
    high_risks = [risk for risk in risk_data if str(risk.get("severity")) in {"High", "Critical"}]
    total_budget = _number(metrics.get("total_budget")) or _number(project.get("contract_value")) or 0
    actual_cost = _number(metrics.get("actual_cost")) or 0
    forecast_cost = _number(metrics.get("forecast_cost")) or 0
    delayed_activities = int(_number(metrics.get("delayed_activity_count")) or 0)
    status = _project_status(metrics, high_risks)

    if not result:
        return _empty_dashboard(project, active_projects)

    return {
        "kpis": {
            "active_projects": active_projects,
            "total_budget": total_budget,
            "actual_cost": actual_cost,
            "forecast_cost": forecast_cost,
            "cpi": _number(metrics.get("cpi")),
            "spi": _number(metrics.get("spi")),
            "delayed_activities": delayed_activities,
            "high_risk_items": len(high_risks),
        },
        "cost_overview": _normalize_cost_series(dashboard_data.get("cost_overview") or []),
        "schedule_performance": {
            "planned_progress": _number(schedule.get("planned_progress")) or 0,
            "actual_progress": _number(schedule.get("actual_progress")) or 0,
            "variance": _number(schedule.get("variance")) or 0,
            "delay_days": int(_number(schedule.get("delay_days")) or 0),
            "stages": schedule.get("stages") or [],
        },
        "project_status": _status_distribution(status, active_projects),
        "top_risks": [_risk_for_api(risk) for risk in risk_data[:8]],
        "upcoming_milestones": _milestones(schedule.get("milestones") or [], project),
        "document_control": {
            "uploaded_files": int(document_control.get("uploaded_files") or 0),
            "pending_review": int(document_control.get("pending_review") or 0),
            "approved_documents": int(document_control.get("approved_documents") or 0),
            "missing_documents": int(document_control.get("missing_documents") or 0),
        },
        "management_summary": _management_summary(metrics, risk_data, dashboard_data),
        "reports": [_report_for_api(row, project) for row in list(reports or [])[:20]],
        "project": {
            "id": project.get("id") or project.get("project_id"),
            "name": project.get("project_name") or (dashboard_data.get("project") or {}).get("name") or "DevBareun Project",
            "location": project.get("location"),
            "type": project.get("project_type") or project.get("current_status"),
            "status": project.get("current_status") or status,
        },
        "last_updated": result.get("created_at") or dashboard_data.get("calculated_at") or datetime.utcnow().isoformat(),
        "empty_state": False,
        "message": "Dashboard generated from the latest completed project performance review.",
    }


def build_portfolio_dashboard(
    *,
    projects: Iterable[Dict[str, Any]],
    analysis_results: Iterable[Dict[str, Any]],
    reports: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    project_rows = list(projects or [])
    result_rows = list(analysis_results or [])
    if not result_rows:
        return _empty_dashboard({}, len(project_rows))
    dashboards = [build_executive_dashboard(project=_match_project(project_rows, row), analysis_result=row) for row in result_rows]
    total_budget = sum(_number((item.get("kpis") or {}).get("total_budget")) or 0 for item in dashboards)
    actual_cost = sum(_number((item.get("kpis") or {}).get("actual_cost")) or 0 for item in dashboards)
    forecast_cost = sum(_number((item.get("kpis") or {}).get("forecast_cost")) or 0 for item in dashboards)
    high_risks = sum(int((item.get("kpis") or {}).get("high_risk_items") or 0) for item in dashboards)
    delayed = sum(int((item.get("kpis") or {}).get("delayed_activities") or 0) for item in dashboards)
    cpi_values = [_number((item.get("kpis") or {}).get("cpi")) for item in dashboards if _number((item.get("kpis") or {}).get("cpi")) is not None]
    spi_values = [_number((item.get("kpis") or {}).get("spi")) for item in dashboards if _number((item.get("kpis") or {}).get("spi")) is not None]

    statuses: Dict[str, int] = {"On Track": 0, "Watch": 0, "Delayed": 0, "Critical": 0, "No Data": 0}
    top_risks: List[Dict[str, Any]] = []
    milestones: List[Dict[str, Any]] = []
    for item in dashboards:
        for status in item.get("project_status") or []:
            statuses[status.get("status")] = statuses.get(status.get("status"), 0) + int(status.get("count") or 0)
        top_risks.extend(item.get("top_risks") or [])
        milestones.extend(item.get("upcoming_milestones") or [])

    return {
        "kpis": {
            "active_projects": len(project_rows),
            "total_budget": round(total_budget, 2),
            "actual_cost": round(actual_cost, 2),
            "forecast_cost": round(forecast_cost, 2),
            "cpi": round(sum(cpi_values) / len(cpi_values), 2) if cpi_values else None,
            "spi": round(sum(spi_values) / len(spi_values), 2) if spi_values else None,
            "delayed_activities": delayed,
            "high_risk_items": high_risks,
        },
        "cost_overview": _merge_cost_series([item.get("cost_overview") or [] for item in dashboards]),
        "schedule_performance": _portfolio_schedule(dashboards),
        "project_status": _status_rows(statuses),
        "top_risks": top_risks[:8],
        "upcoming_milestones": milestones[:8],
        "document_control": _portfolio_documents(dashboards),
        "management_summary": {
            "overall_status": "Portfolio view is generated from completed project performance reviews.",
            "main_delay_reason": "Review projects with delayed stages and open schedule risks first.",
            "cost_pressure": "Cost pressure is based on CPI, forecast cost and committed cost trend.",
            "immediate_action": "Open the highest risk project and review recovery actions.",
            "confidence_score": _portfolio_confidence(result_rows),
        },
        "reports": [_report_for_api(row, {}) for row in list(reports or [])[:20]],
        "last_updated": datetime.utcnow().isoformat(),
        "empty_state": False,
        "message": "Portfolio dashboard generated from saved analysis results.",
    }


def _empty_dashboard(project: Dict[str, Any], active_projects: int = 0) -> Dict[str, Any]:
    return {
        "kpis": {
            "active_projects": active_projects,
            "total_budget": _number(project.get("contract_value")) or 0,
            "actual_cost": 0,
            "forecast_cost": 0,
            "cpi": None,
            "spi": None,
            "delayed_activities": 0,
            "high_risk_items": 0,
        },
        "cost_overview": [],
        "schedule_performance": {"planned_progress": 0, "actual_progress": 0, "variance": 0, "delay_days": 0, "stages": []},
        "project_status": _status_rows({"On Track": 0, "Watch": 0, "Delayed": 0, "Critical": 0, "No Data": max(1, active_projects)}),
        "top_risks": [],
        "upcoming_milestones": [],
        "document_control": {"uploaded_files": 0, "pending_review": 0, "approved_documents": 0, "missing_documents": 0},
        "management_summary": {
            "overall_status": EMPTY_STATE_TEXT,
            "main_delay_reason": "No completed project performance review is available yet.",
            "cost_pressure": "Cost pressure will appear after uploaded files are reviewed.",
            "immediate_action": "Upload project files and start project review.",
            "confidence_score": 0,
        },
        "reports": [],
        "last_updated": None,
        "empty_state": True,
        "message": EMPTY_STATE_TEXT,
    }


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _normalize_cost_series(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for row in rows:
        result.append({
            "period": row.get("period"),
            "budget": _number(row.get("budget")) or 0,
            "actual": _number(row.get("actual")) or _number(row.get("actualCost")) or 0,
            "forecast": _number(row.get("forecast")) or 0,
            "committed": _number(row.get("committed")) or _number(row.get("committedCost")) or 0,
        })
    return result


def _project_status(metrics: Dict[str, Any], high_risks: List[Dict[str, Any]]) -> str:
    delay = _number(metrics.get("delay_days")) or 0
    cpi = _number(metrics.get("cpi"))
    spi = _number(metrics.get("spi"))
    if any(str(risk.get("severity")) == "Critical" for risk in high_risks) or delay >= 30 or (cpi is not None and cpi < 0.85) or (spi is not None and spi < 0.85):
        return "Critical"
    if delay >= 14 or high_risks:
        return "Delayed"
    if delay > 0 or (cpi is not None and cpi < 0.95) or (spi is not None and spi < 0.95):
        return "Watch"
    return "On Track"


def _status_distribution(status: str, active_projects: int) -> List[Dict[str, Any]]:
    rows = {"On Track": 0, "Watch": 0, "Delayed": 0, "Critical": 0, "No Data": 0}
    rows[status] = max(1, active_projects)
    return _status_rows(rows)


def _status_rows(statuses: Dict[str, int]) -> List[Dict[str, Any]]:
    total = sum(int(value or 0) for value in statuses.values()) or 1
    return [
        {"status": key, "count": int(statuses.get(key) or 0), "percentage": round((int(statuses.get(key) or 0) / total) * 100, 1)}
        for key in ["On Track", "Watch", "Delayed", "Critical", "No Data"]
    ]


def _risk_for_api(risk: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "risk_title": risk.get("risk_title") or risk.get("title"),
        "title": risk.get("title") or risk.get("risk_title"),
        "category": risk.get("category"),
        "severity": risk.get("severity"),
        "impact": risk.get("impact"),
        "recommended_action": risk.get("recommended_action") or risk.get("action"),
        "action": risk.get("action") or risk.get("recommended_action"),
        "description": risk.get("description") or risk.get("explanation"),
        "probability": risk.get("probability"),
        "status": risk.get("status") or "Open",
    }


def _milestones(rows: List[Dict[str, Any]], project: Dict[str, Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in rows:
        output.append({
            "milestone_name": row.get("name") or row.get("milestone_name"),
            "name": row.get("name") or row.get("milestone_name"),
            "project": project.get("project_name") or "Project",
            "due_date": row.get("due_date") or row.get("dueDate"),
            "status": row.get("status") or "Upcoming",
            "days_remaining": row.get("days_remaining") or row.get("daysRemaining") or 0,
        })
    return output


def _management_summary(metrics: Dict[str, Any], risks: List[Dict[str, Any]], dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
    delay = int(_number(metrics.get("delay_days")) or 0)
    cpi = _number(metrics.get("cpi"))
    spi = _number(metrics.get("spi"))
    high = [risk for risk in risks if str(risk.get("severity")) in {"High", "Critical"}]
    return {
        "overall_status": "Project control is within target range." if not high and delay <= 7 else "Project control needs management attention.",
        "main_delay_reason": "Schedule variance and open risks are the main delay drivers." if delay else "No confirmed delay driver is available from the latest review.",
        "cost_pressure": "Cost pressure is above target." if cpi is not None and cpi < 0.95 else "Cost pressure is controlled or not yet confirmed.",
        "immediate_action": (high[0].get("recommended_action") or high[0].get("action")) if high else "Continue weekly project control updates.",
        "confidence_score": dashboard_data.get("confidence_score") or 0,
        "cpi": cpi,
        "spi": spi,
    }


def _match_project(projects: List[Dict[str, Any]], result: Dict[str, Any]) -> Dict[str, Any]:
    project_id = str(result.get("project_id") or "")
    for project in projects:
        if str(project.get("id") or project.get("project_id")) == project_id:
            return project
    return {}


def _merge_cost_series(series_list: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for series in series_list:
        for row in _normalize_cost_series(series):
            period = row.get("period") or "Period"
            target = merged.setdefault(period, {"period": period, "budget": 0, "actual": 0, "forecast": 0, "committed": 0})
            for key in ["budget", "actual", "forecast", "committed"]:
                target[key] = round(float(target[key]) + float(row.get(key) or 0), 2)
    return list(merged.values())


def _portfolio_schedule(dashboards: List[Dict[str, Any]]) -> Dict[str, Any]:
    schedules = [item.get("schedule_performance") or {} for item in dashboards]
    count = len(schedules) or 1
    return {
        "planned_progress": round(sum(_number(row.get("planned_progress")) or 0 for row in schedules) / count, 1),
        "actual_progress": round(sum(_number(row.get("actual_progress")) or 0 for row in schedules) / count, 1),
        "variance": round(sum(_number(row.get("variance")) or 0 for row in schedules) / count, 1),
        "delay_days": int(sum(_number(row.get("delay_days")) or 0 for row in schedules) / count),
        "stages": (schedules[0].get("stages") if schedules else []) or [],
    }


def _portfolio_documents(dashboards: List[Dict[str, Any]]) -> Dict[str, int]:
    totals = {"uploaded_files": 0, "pending_review": 0, "approved_documents": 0, "missing_documents": 0}
    for item in dashboards:
        summary = item.get("document_control") or {}
        for key in totals:
            totals[key] += int(summary.get(key) or 0)
    return totals


def _portfolio_confidence(results: List[Dict[str, Any]]) -> float:
    scores = [_number(row.get("confidence_score")) for row in results if _number(row.get("confidence_score")) is not None]
    return round(sum(scores) / len(scores), 1) if scores else 0


def _report_for_api(row: Dict[str, Any], project: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id") or row.get("report_id"),
        "report_name": row.get("report_name") or row.get("name") or f"{project.get('project_name', 'Project')} Report",
        "name": row.get("report_name") or row.get("name") or "Project Control Report",
        "project_name": project.get("project_name") or row.get("project_name"),
        "project": project.get("project_name") or row.get("project_name") or "Project",
        "report_type": row.get("report_type") or row.get("type") or "Project Control Report",
        "type": row.get("report_type") or row.get("type") or "Project Control",
        "created_date": row.get("created_at"),
        "created": row.get("created_at"),
        "format": row.get("format") or row.get("report_format") or "PDF",
        "status": row.get("status") or "Ready",
    }
