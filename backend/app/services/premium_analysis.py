from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List

from ..analysis_types import PREMIUM_ANALYSIS_TYPE

NOT_CALCULATED = "Not calculated — required file or fields missing."


def analyze_full_project_control_premium(
    normalized: Dict[str, Any],
    analytics: Dict[str, Any] | None = None,
    risks: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    analytics = analytics or {}
    metrics = analytics.get("metrics") or {}
    risks_list = list(risks or [])
    project = normalized.get("project_info") or {}
    currency = project.get("currency") or "USD"
    group_status = file_group_status(normalized)
    data_quality = _data_quality(group_status)

    schedule = _schedule_analysis(normalized, metrics)
    cost = _cost_payment_analysis(normalized, metrics, currency)
    workforce = _workforce_analysis(normalized, metrics)
    material = _material_continuity(normalized)
    risk_section = _risk_register_analysis(normalized, risks_list)
    recovery = _recovery_actions(schedule, cost, workforce, material, risk_section)
    summary = _executive_summary(schedule, cost, material, risk_section, recovery, data_quality)

    missing_inputs = [
        {"group": name, "status": info["status"], "required_files": info["required_files"]}
        for name, info in group_status.items()
        if info["status"] == "missing"
    ]
    warnings = list(dict.fromkeys((normalized.get("warnings") or []) + _missing_warnings(missing_inputs)))

    return {
        "analysis_type": PREMIUM_ANALYSIS_TYPE,
        "title": "Full Project Control Premium Dashboard",
        "executive_summary": summary,
        "kpis": {
            "project_status": summary.get("overall_project_status"),
            "planned_progress_percent": _value_or_missing(schedule, "planned_progress_percent"),
            "actual_progress_percent": _value_or_missing(schedule, "actual_progress_percent"),
            "schedule_gap_percent": _value_or_missing(schedule, "schedule_gap_percent"),
            "delay_days": _value_or_missing(schedule, "delay_days"),
            "contract_value": _value_or_missing(cost, "contract_value"),
            "actual_cost": _value_or_missing(cost, "actual_cost"),
            "approved_payment": _value_or_missing(cost, "approved_payment"),
            "remaining_cost": _value_or_missing(cost, "remaining_cost"),
            "cost_variance_percent": _value_or_missing(cost, "cost_variance_percent"),
            "current_workforce": _value_or_missing(workforce, "current_workforce"),
            "required_workforce": _value_or_missing(workforce, "required_workforce"),
            "critical_low_stock_items": _value_or_missing(material, "critical_low_stock_items"),
            "top_risk_count": len(risk_section.get("top_risks") or []),
            "currency": currency,
        },
        "schedule_analysis": schedule,
        "cost_payment_analysis": cost,
        "workforce_analysis": workforce,
        "material_continuity": material,
        "risk_register_analysis": risk_section,
        "recovery_actions": recovery,
        "data_quality": data_quality,
        "file_group_status": group_status,
        "missing_inputs": missing_inputs,
        "warnings": warnings,
        "generated_at": date.today().isoformat(),
    }


def file_group_status(normalized: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    sheets = (((normalized.get("evidence") or {}).get("sheet_profiles")) or [])
    sheet_types = {str(sheet.get("detected_type") or "").lower() for sheet in sheets}
    mapped_fields = set()
    for sheet in sheets:
        mapped_fields.update((sheet.get("mapped_columns") or {}).keys())

    def has_metric(section: str, name: str) -> bool:
        return _metric_value(normalized, section, name) is not None

    groups = {
        "Schedule": {
            "available": bool({"schedule", "progress"} & sheet_types) or has_metric("progress_data", "planned_progress_percent") or has_metric("progress_data", "actual_progress_percent"),
            "strong": has_metric("progress_data", "planned_progress_percent") and has_metric("progress_data", "actual_progress_percent"),
            "required_files": ["Baseline schedule", "Actual progress"],
        },
        "Cost": {
            "available": bool({"cost"} & sheet_types) or has_metric("cost_data", "total_budget") or has_metric("cost_data", "actual_cost"),
            "strong": has_metric("cost_data", "total_budget") and (has_metric("cost_data", "actual_cost") or has_metric("cost_data", "planned_cost")),
            "required_files": ["Cost estimate / BOQ", "Actual cost report"],
        },
        "Payment": {
            "available": bool({"progress"} & sheet_types) or has_metric("cost_data", "actual_cost"),
            "strong": has_metric("cost_data", "actual_cost"),
            "required_files": ["F-2 / progress payment"],
        },
        "Workforce": {
            "available": bool({"workforce"} & sheet_types) or has_metric("manpower_data", "current_workforce") or has_metric("manpower_data", "required_workforce"),
            "strong": has_metric("manpower_data", "current_workforce") and has_metric("manpower_data", "required_workforce"),
            "required_files": ["Workforce report"],
        },
        "Material": {
            "available": bool({"material", "procurement"} & sheet_types),
            "strong": bool({"material", "procurement"} & sheet_types and {"available_quantity", "required_quantity", "delivery_date"} & mapped_fields),
            "required_files": ["Material stock list", "Procurement status"],
        },
        "Risk": {
            "available": bool({"risk", "report"} & sheet_types) or bool(normalized.get("risk_signals")),
            "strong": bool({"risk"} & sheet_types and {"probability", "impact", "risk_score", "status"} & mapped_fields),
            "required_files": ["Risk register"],
        },
    }
    result: Dict[str, Dict[str, Any]] = {}
    for name, info in groups.items():
        status = "active" if info["strong"] else "partial" if info["available"] else "missing"
        result[name] = {
            "status": status,
            "available": bool(info["available"]),
            "required_files": info["required_files"],
        }
    return result


def _schedule_analysis(normalized: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    planned = _metric_value(normalized, "progress_data", "planned_progress_percent")
    actual = _metric_value(normalized, "progress_data", "actual_progress_percent")
    gap = None if planned is None or actual is None else round(float(planned) - float(actual), 2)
    delay_days = _schedule_value(normalized, "delay_days")
    estimated_finish = _schedule_value(normalized, "forecast_finish")
    status = _section_status([planned, actual, delay_days, estimated_finish], required=2)
    critical = bool((delay_days or 0) >= 14 or (gap or 0) >= 10)
    return {
        "status": status,
        "planned_progress_percent": planned,
        "actual_progress_percent": actual,
        "schedule_gap_percent": gap,
        "delay_days": delay_days if delay_days not in (None, "") else None,
        "critical_delay_risk": critical if status != "Missing" else None,
        "estimated_completion_impact": estimated_finish or (f"{int(delay_days)} days beyond baseline" if delay_days else NOT_CALCULATED),
        "message": _missing_message(status),
    }


def _cost_payment_analysis(normalized: Dict[str, Any], metrics: Dict[str, Any], currency: str) -> Dict[str, Any]:
    contract_value = _metric_value(normalized, "cost_data", "total_budget") or metrics.get("total_budget")
    actual_cost = _metric_value(normalized, "cost_data", "actual_cost") or metrics.get("actual_cost")
    approved_payment = _metric_value(normalized, "cost_data", "actual_cost")
    remaining = None if contract_value is None or actual_cost is None else round(float(contract_value) - float(actual_cost), 2)
    variance = metrics.get("cost_variance")
    variance_percent = None
    if contract_value not in (None, 0) and variance is not None:
        variance_percent = round((float(variance) / float(contract_value)) * 100, 2)
    status = _section_status([contract_value, actual_cost, approved_payment], required=2)
    return {
        "status": status,
        "currency": currency,
        "contract_value": contract_value,
        "actual_cost": actual_cost,
        "approved_payment": approved_payment,
        "remaining_cost": remaining,
        "cost_variance": variance,
        "cost_variance_percent": variance_percent,
        "overrun_risk": bool(variance and float(variance) > 0) if status != "Missing" else None,
        "message": _missing_message(status),
    }


def _workforce_analysis(normalized: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    current = _metric_value(normalized, "manpower_data", "current_workforce")
    required = _metric_value(normalized, "manpower_data", "required_workforce")
    delay_days = metrics.get("delay_days") or _schedule_value(normalized, "delay_days") or 0
    gap = None if current is None or required is None else int(round(float(required) - float(current)))
    low_productivity = bool(gap and gap > 0)
    status = _section_status([current, required], required=2)
    return {
        "status": status,
        "current_workforce": current,
        "required_workforce": required,
        "workforce_gap": gap,
        "productivity_risk": low_productivity if status != "Missing" else None,
        "recommended_workforce_increase": gap if low_productivity and delay_days and delay_days > 0 else None,
        "message": _missing_message(status),
    }


def _material_continuity(normalized: Dict[str, Any]) -> Dict[str, Any]:
    material = (normalized.get("material_data") or [{}])[0] or {}
    source_count = int(material.get("detected_material_sources") or 0)
    status = "Partial" if source_count else "Missing"
    return {
        "status": status,
        "detected_material_sources": source_count,
        "stock_balance": None,
        "critical_low_stock_items": None,
        "days_remaining": None,
        "procurement_delay_risk": bool(source_count) if source_count else None,
        "schedule_link": "Material evidence should be matched to delayed or critical activities." if source_count else NOT_CALCULATED,
        "message": _missing_message(status),
    }


def _risk_register_analysis(normalized: Dict[str, Any], risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    group = file_group_status(normalized)["Risk"]
    top = []
    for item in risks[:8]:
        probability = item.get("probability")
        impact = item.get("impact")
        score = _risk_score(probability, impact, item.get("severity"))
        top.append({
            "risk_title": item.get("risk_title") or item.get("title"),
            "risk_category": item.get("category"),
            "probability": probability,
            "impact": impact,
            "risk_score": score,
            "risk_level": item.get("severity") or _risk_level(score),
            "owner": item.get("responsible_party"),
            "deadline": item.get("deadline"),
            "status": item.get("status"),
            "mitigation": item.get("recommended_action") or item.get("action"),
        })
    status = "Active" if group["status"] == "active" else "Partial" if top else "Missing"
    return {
        "status": status,
        "risk_register_uploaded": group["status"] == "active",
        "system_risks_used": group["status"] != "active" and bool(top),
        "top_risks": top,
        "message": "Risk register missing; system risks are based on schedule, cost, material and data-quality evidence." if group["status"] != "active" and top else _missing_message(status),
    }


def _recovery_actions(schedule: Dict[str, Any], cost: Dict[str, Any], workforce: Dict[str, Any], material: Dict[str, Any], risk: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if schedule.get("delay_days") and workforce.get("recommended_workforce_increase"):
        actions.append(_action("Schedule Recovery", f"Increase workforce by {workforce['recommended_workforce_increase']} workers on delayed work fronts.", "High"))
    if cost.get("overrun_risk"):
        actions.append(_action("Cost Control", "Review cost packages, approved changes and unsupported overruns before the next payment cycle.", "High"))
    if material.get("procurement_delay_risk"):
        actions.append(_action("Material Continuity", "Confirm supplier delivery dates and accelerate procurement for materials linked to delayed work.", "Medium"))
    high_risk = [item for item in risk.get("top_risks") or [] if item.get("risk_level") in {"High", "Critical"}]
    if high_risk:
        actions.append(_action("Risk Register", "Assign owners and deadlines for the highest priority open risks.", "High"))
    if not actions:
        actions.append(_action("Data Completion", "Upload the missing file groups and rerun the project-control review.", "Medium"))
    return actions


def _executive_summary(schedule: Dict[str, Any], cost: Dict[str, Any], material: Dict[str, Any], risk: Dict[str, Any], actions: List[Dict[str, Any]], data_quality: Dict[str, Any]) -> Dict[str, Any]:
    delay_issue = _issue("Schedule", schedule.get("status"), schedule.get("delay_days"), "delay days")
    cost_issue = _issue("Cost", cost.get("status"), cost.get("cost_variance_percent"), "% variance")
    material_issue = "Material continuity requires procurement review." if material.get("procurement_delay_risk") else _missing_message(material.get("status"))
    risk_issue = f"{len(risk.get('top_risks') or [])} risks require review." if risk.get("top_risks") else _missing_message(risk.get("status"))
    overall = "Management attention required" if any(a.get("priority") == "High" for a in actions) else "Review with available data"
    return {
        "overall_project_status": overall,
        "main_delay_issue": delay_issue,
        "main_cost_issue": cost_issue,
        "main_material_issue": material_issue,
        "main_risk_issue": risk_issue,
        "recommended_next_decision": actions[0]["action"] if actions else "Complete missing inputs and rerun analysis.",
        "data_quality_status": data_quality.get("overall_status"),
    }


def _data_quality(groups: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    section_status = {
        "Schedule Analysis": _title_status(groups["Schedule"]["status"]),
        "Cost Control": _combined_status([groups["Cost"]["status"], groups["Payment"]["status"]]),
        "Workforce Productivity": _title_status(groups["Workforce"]["status"]),
        "Material Continuity": _title_status(groups["Material"]["status"]),
        "Risk Register": _title_status(groups["Risk"]["status"]),
    }
    active = sum(1 for status in section_status.values() if status == "Active")
    partial = sum(1 for status in section_status.values() if status == "Partial")
    overall = "Active" if active >= 4 else "Partial" if active or partial else "Missing"
    return {"overall_status": overall, "sections": section_status}


def _metric_value(normalized: Dict[str, Any], section: str, name: str) -> float | None:
    for item in normalized.get(section) or []:
        if item.get("name") == name:
            return _number(item.get("value"))
    return None


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


def _section_status(values: List[Any], required: int) -> str:
    count = len([value for value in values if value not in (None, "")])
    if count >= required:
        return "Active"
    return "Partial" if count else "Missing"


def _title_status(status: str) -> str:
    return {"active": "Active", "partial": "Partial", "missing": "Missing"}.get(str(status).lower(), str(status or "Missing").title())


def _combined_status(statuses: List[str]) -> str:
    titled = [_title_status(status) for status in statuses]
    if all(status == "Active" for status in titled):
        return "Active"
    if any(status in {"Active", "Partial"} for status in titled):
        return "Partial"
    return "Missing"


def _missing_message(status: Any) -> str:
    return NOT_CALCULATED if str(status).lower() == "missing" else ""


def _value_or_missing(section: Dict[str, Any], key: str) -> Any:
    value = section.get(key)
    return value if value not in (None, "") else NOT_CALCULATED


def _risk_score(probability: Any, impact: Any, severity: Any) -> int | None:
    prob = _number(probability)
    if prob is not None:
        base = prob * 100 if prob <= 1 else prob
        multiplier = {"Low": 0.35, "Medium": 0.55, "High": 0.78, "Critical": 0.95}.get(str(severity or ""), 0.55)
        return int(round(min(100, base * multiplier)))
    return {"Low": 25, "Medium": 50, "High": 75, "Critical": 92}.get(str(severity or ""), None)


def _risk_level(score: int | None) -> str:
    if score is None:
        return "Medium"
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def _action(module: str, action: str, priority: str) -> Dict[str, Any]:
    return {"module": module, "action": action, "priority": priority, "status": "Open"}


def _issue(label: str, status: Any, value: Any, suffix: str) -> str:
    if str(status).lower() == "missing":
        return f"{label}: {NOT_CALCULATED}"
    if value in (None, ""):
        return f"{label}: review required with partial data."
    return f"{label}: {value} {suffix}."


def _missing_warnings(missing_inputs: List[Dict[str, Any]]) -> List[str]:
    return [f"{item['group']} input is missing for Full Project Control Premium." for item in missing_inputs]
