from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import ParsedProjectData
from .statistics_engine import build_statistical_analytics


def _round(value: Optional[float], ndigits: int = 1) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), ndigits)


def _status_from_score(score: Optional[int]) -> str:
    if score is None:
        return "Data review required"
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "At Risk"
    if score >= 40:
        return "Watch"
    return "Controlled"


def _risk_level_from_score(score: Optional[int]) -> str:
    if score is None:
        return "Not available"
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _component_score(value: Optional[float], scale: float) -> Optional[float]:
    if value is None:
        return None
    return max(0.0, min(100.0, value * scale))



def _has_progress_payment_source(parsed: ParsedProjectData) -> bool:
    """Return True when uploaded data contains a credible actual/progress source.

    Cost and schedule comparisons must be based on baseline + actual evidence.
    A smeta/cost-estimate file alone is not enough to calculate actual cost,
    execution %, variance or delay. This protects the dashboard from imaginary
    results when only baseline data is uploaded.
    """
    evidence = parsed.evidence or {}
    if evidence.get("f2_completed_amount") or evidence.get("f2_sheets"):
        return True
    if evidence.get("actual_execution_source") or evidence.get("az_f2_parser"):
        return True
    if any(s.detected_type == "progress" for s in parsed.sheets):
        return True
    if any((s.mapped_columns or {}).get("actual_cost") or (s.mapped_columns or {}).get("actual_execution") for s in parsed.sheets):
        return True
    return False


def _has_schedule_actual_source(parsed: ParsedProjectData) -> bool:
    if parsed.actual_execution is not None or parsed.estimated_finish:
        return True
    if any((s.mapped_columns or {}).get("actual_execution") or (s.mapped_columns or {}).get("estimated_finish") for s in parsed.sheets):
        return True
    return False


def apply_baseline_actual_guardrails(parsed: ParsedProjectData, analysis_type: str | None = "all") -> None:
    """Guardrail: no baseline-vs-actual comparison without actual evidence.

    - Cost: smeta/cost estimate alone can create a budget-only dashboard, but not
      actual cost, remaining value, cost variance or actual execution.
    - Schedule: baseline schedule alone can create a planning summary, but not
      progress gap, delay or forecast comparison.
    """
    t = _clean_analysis_type(analysis_type)
    warnings = parsed.warnings

    # Workforce/Productivity dashboards must not be polluted by generic cost/progress
    # numbers that can appear inside template examples or calculation rows.
    # For workforce analysis, authoritative workforce values come from the
    # productivity module summary, not from arbitrary numeric cells.
    if t == "workforce":
        productivity = (parsed.evidence or {}).get("workforce_productivity") or {}
        summary = productivity.get("summary") or {}
        if summary.get("total_actual_workers") is not None:
            parsed.workforce_current = int(summary.get("total_actual_workers") or 0)
        if summary.get("total_required_workers") is not None:
            parsed.workforce_required = int(summary.get("total_required_workers") or 0)

        # Clear unrelated commercial/schedule KPIs for pure workforce analysis.
        parsed.total_cost = None
        parsed.planned_cost = None
        parsed.actual_cost = None
        parsed.cost_variance_percent = None
        parsed.planned_execution = None
        parsed.actual_execution = None
        parsed.delay_days = None
        parsed.baseline_finish = None
        parsed.estimated_finish = None
        return

    # Cost/progress comparison requires F-2/payment/actual source.
    if t in {"cost", "progress", "all"} and parsed.total_cost is not None:
        has_actual = _has_progress_payment_source(parsed)
        if not has_actual:
            if parsed.actual_cost is not None:
                parsed.evidence["unconfirmed_actual_cost"] = parsed.actual_cost
                parsed.actual_cost = None
            if parsed.actual_execution is not None:
                parsed.evidence["unconfirmed_actual_execution"] = parsed.actual_execution
                parsed.actual_execution = None
            parsed.cost_variance_percent = None
            parsed.evidence["cost_actual_data_missing"] = True
            msg = "Actual cost / progress payment data was not found. Cost variance and actual execution require confirmed actual data."
            if msg not in warnings:
                warnings.append(msg)

    # Schedule comparison requires actual/progress update data.
    schedule_baseline_present = parsed.planned_execution is not None or parsed.baseline_finish is not None or any(s.detected_type == "schedule" for s in parsed.sheets)
    if t in {"schedule", "all"} and schedule_baseline_present and not _has_schedule_actual_source(parsed):
        parsed.delay_days = None
        parsed.evidence["schedule_actual_data_missing"] = True
        msg = "Actual progress data was not found. Schedule comparison cannot be calculated reliably without actual progress, actual finish or forecast finish data."
        if msg not in warnings:
            warnings.append(msg)


def compute_risk(parsed: ParsedProjectData) -> Dict[str, Any]:
    gap = None
    if parsed.planned_execution is not None and parsed.actual_execution is not None:
        gap = max(0.0, parsed.planned_execution - parsed.actual_execution)

    schedule_from_gap = _component_score(gap, 4.0) if gap is not None else None
    schedule_from_delay = _component_score(float(parsed.delay_days), 1.6) if parsed.delay_days is not None and parsed.delay_days > 0 else None
    schedule_risk = max([v for v in [schedule_from_gap, schedule_from_delay] if v is not None], default=None)

    cost_risk = _component_score(abs(parsed.cost_variance_percent), 6.0) if parsed.cost_variance_percent is not None else None

    workforce_risk = None
    if parsed.workforce_current is not None and parsed.workforce_required:
        workforce_gap = max(0, parsed.workforce_required - parsed.workforce_current)
        workforce_risk = min(100.0, (workforce_gap / parsed.workforce_required) * 100 * 2.8)

    procurement_risk = 45.0 if any(s.detected_type == "procurement" for s in parsed.sheets) else None
    quality_risk = 50.0 if parsed.warnings else None

    components = {
        "schedule": schedule_risk,
        "cost": cost_risk,
        "labor": workforce_risk,
        "procurement": procurement_risk,
        "quality": quality_risk,
    }
    weights = {
        "schedule": 0.35,
        "cost": 0.25,
        "labor": 0.20,
        "procurement": 0.15,
        "quality": 0.05,
    }
    available = {k: v for k, v in components.items() if v is not None}
    if not available:
        score = None
    else:
        weight_sum = sum(weights[k] for k in available)
        score = round(sum(available[k] * weights[k] for k in available) / weight_sum)

    return {
        "score": int(score) if score is not None else None,
        "level": _risk_level_from_score(int(score) if score is not None else None),
        "components": {k: (_round(v, 1) if v is not None else None) for k, v in components.items()},
        "schedule_gap_percent": _round(gap, 1),
    }


def confidence_score(parsed: ParsedProjectData, risk: Dict[str, Any]) -> int:
    score = 0
    if parsed.project_name:
        score += 10
    if parsed.currency:
        score += 8
    if parsed.planned_execution is not None:
        score += 14
    if parsed.actual_execution is not None:
        score += 14
    if parsed.delay_days is not None or (parsed.baseline_finish and parsed.estimated_finish):
        score += 12
    if parsed.cost_variance_percent is not None or parsed.planned_cost or parsed.actual_cost:
        score += 12
    if parsed.workforce_current is not None:
        score += 8
    if parsed.sheets:
        avg_sheet_conf = sum(s.confidence for s in parsed.sheets) / max(1, len(parsed.sheets))
        score += int(min(22, avg_sheet_conf * 0.22))
    if risk["score"] is not None:
        score += 10
    if _actual_cost_needs_confirmation(parsed):
        score -= 12
    return max(0, min(100, score))


def build_summary(parsed: ParsedProjectData, risk: Dict[str, Any], confidence: int, analysis_type: str | None = "all") -> str:
    parts: List[str] = []
    t = _clean_analysis_type(analysis_type)
<<<<<<< HEAD
=======
    if t == "material":
        material_count = _available_sheet_count(parsed, "procurement") + _available_sheet_count(parsed, "material")
        if material_count:
            parts.append(f"Material/procurement evidence was detected in {material_count} sheet(s).")
        else:
            parts.append("Material continuity data was not clearly detected from the uploaded files.")
        parts.append("Confirm stock levels, supplier delivery dates, critical materials and alternative procurement actions before using continuity conclusions.")
        parts.append(f"Dashboard confidence is {confidence}/100 based on detected sheets, mapped columns and extracted KPI evidence.")
        return " ".join(parts)
    if t == "risk":
        register = build_risk_register(parsed, risk)
        if risk.get("score") is not None:
            parts.append(f"Combined risk score is {risk.get('score')}/100 with {risk.get('level')} status.")
        parts.append(f"Risk & Decisions dashboard prepared {len(register)} risk/decision item(s) from available evidence.")
        parts.append("Use the recommended actions as management prompts and confirm unclear source data before final decisions.")
        parts.append(f"Dashboard confidence is {confidence}/100 based on detected sheets, mapped columns and extracted KPI evidence.")
        return " ".join(parts)

>>>>>>> a71c3ae48045c65514ab1d10b3c6e7f098eb1be3
    if t == "cost":
        baseline = _cost_baseline(parsed)
        remaining = _remaining_cost(parsed)
        if baseline is not None:
            parts.append(f"Cost Estimate / Smeta baseline is {baseline:,.2f} {parsed.currency or ''}.")
        if parsed.actual_cost is not None and not _actual_cost_needs_confirmation(parsed):
            parts.append(f"Confirmed progress payment / actual cost is {float(parsed.actual_cost):,.2f} {parsed.currency or ''}.")
        elif _actual_cost_needs_confirmation(parsed):
            parts.append("Detected progress payment / actual cost requires confirmation before commercial use.")
        else:
            parts.append("Confirmed progress payment / actual cost data was not clearly detected.")
        if remaining is not None:
            parts.append(f"Remaining value is {remaining:,.2f} {parsed.currency or ''}.")
        if parsed.cost_variance_percent is not None:
            direction = "above" if parsed.cost_variance_percent > 0 else "below" if parsed.cost_variance_percent < 0 else "equal to"
            parts.append(f"Cost variance is {abs(parsed.cost_variance_percent):g}% {direction} the smeta baseline.")
        parts.append(f"Dashboard confidence is {confidence}/100 based on detected cost, progress payment and mapped KPI evidence.")
        return " ".join(parts)
    productivity_summary = _workforce_productivity_summary(parsed)
    workforce_only = bool(productivity_summary.get("activities_checked")) and parsed.total_cost is None and parsed.planned_execution is None and parsed.actual_execution is None

    if not workforce_only:
        if parsed.planned_execution is not None and parsed.actual_execution is not None:
            gap = risk.get("schedule_gap_percent")
            if gap and gap > 0:
                parts.append(f"The project is {gap:g} percentage points behind the planned baseline.")
            else:
                parts.append("The available plan/fact progress data does not show a negative progress gap.")
        elif parsed.actual_execution is not None:
            parts.append(f"Actual execution was detected at {parsed.actual_execution:g}%, but planned baseline progress was not clearly mapped.")
        else:
            parts.append("Progress indicators were not confidently mapped from the uploaded files.")

    if parsed.delay_days is not None:
        if parsed.delay_days > 0:
            parts.append(f"The current schedule impact is approximately {parsed.delay_days} days beyond the baseline.")
        else:
            parts.append("No positive schedule delay was detected from the available finish dates.")

    if parsed.cost_variance_percent is not None:
        direction = "above" if parsed.cost_variance_percent >= 0 else "below"
        parts.append(f"Cost variance is {abs(parsed.cost_variance_percent):g}% {direction} baseline.")
    elif parsed.total_cost is not None:
        parts.append(f"The detected smeta/contract baseline is approximately {parsed.total_cost:,.2f} {parsed.currency or ''}.")
        if parsed.evidence.get("cost_actual_data_missing"):
            parts.append("Actual cost or progress payment data was not confirmed, so cost variance and actual execution are not calculated.")

    if parsed.evidence.get("schedule_actual_data_missing"):
        parts.append("Baseline schedule data was detected, but actual progress or forecast data is missing; schedule comparison is held until actual data is provided.")

    if _actual_cost_needs_confirmation(parsed):
        parts.append("The detected actual completed cost exceeds the smeta/contract baseline and is held for mapping confirmation before commercial use.")

    if productivity_summary.get("activities_checked"):
        parts.append(
            f"Workforce productivity review checked {productivity_summary.get('activities_checked')} activities; "
            f"{productivity_summary.get('activities_with_shortage', 0)} activities show manpower shortage and "
            f"maximum duration risk is {productivity_summary.get('max_delay_risk_days', 0):g} days."
        )

    if parsed.workforce_current is not None and parsed.workforce_required:
        gap = parsed.workforce_required - parsed.workforce_current
        if gap > 0:
            parts.append(f"Workforce is {gap} workers below the indicated recovery requirement.")
        else:
            parts.append("Current workforce meets or exceeds the indicated requirement.")

    parts.append(f"Dashboard confidence is {confidence}/100 based on detected sheets, mapped columns and extracted KPI evidence.")
    return " ".join(parts)


def build_risk_register(parsed: ParsedProjectData, risk: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    gap = risk.get("schedule_gap_percent")
    if gap is not None and gap > 0:
        rows.append({
            "risk": "Schedule delay",
            "level": "High" if gap >= 15 or (parsed.delay_days or 0) >= 30 else "Medium",
            "reason": f"Actual progress is {gap:g} percentage points below plan.",
            "action": "Prepare a recovery schedule and increase control of critical activities.",
        })
    if parsed.cost_variance_percent is not None and parsed.cost_variance_percent > 0:
        rows.append({
            "risk": "Cost variance",
            "level": "High" if parsed.cost_variance_percent >= 10 else "Medium",
            "reason": f"Cost variance is {parsed.cost_variance_percent:g}% above baseline.",
            "action": "Review cost variance by work package and freeze unsupported overruns.",
        })
    if _actual_cost_needs_confirmation(parsed):
        info = parsed.evidence.get("needs_confirmation_actual_cost") or {}
        reason = "Detected actual completed cost exceeds the smeta/contract baseline."
        if info.get("detected_actual_cost") and info.get("smeta_total"):
            reason = f"Detected actual completed cost ({info.get('detected_actual_cost'):,.2f}) exceeds smeta/contract total ({info.get('smeta_total'):,.2f})."
        rows.append({
            "risk": "Commercial data confirmation",
            "level": "High",
            "reason": reason,
            "action": "Confirm the correct progress payment cumulative total, VAT treatment, duplicate totals or approved variation before using this value commercially.",
        })
    if parsed.workforce_current is not None and parsed.workforce_required and parsed.workforce_current < parsed.workforce_required:
        rows.append({
            "risk": "Workforce gap",
            "level": "High",
            "reason": f"Current workforce is {parsed.workforce_current}; required workforce is {parsed.workforce_required}.",
            "action": "Increase critical crews and track daily manpower against recovery targets.",
        })
    if parsed.evidence.get("cost_actual_data_missing"):
        rows.append({
            "risk": "Actual cost data missing",
            "level": "Medium",
            "reason": "Cost estimate / smeta data was detected, but no confirmed actual cost or progress payment source was found.",
            "action": "Upload progress payment, invoice or confirmed actual cost data before calculating cost variance or actual execution.",
        })
    if parsed.evidence.get("schedule_actual_data_missing"):
        rows.append({
            "risk": "Actual schedule data missing",
            "level": "Medium",
            "reason": "Baseline schedule data was detected, but actual progress or forecast finish data was not found.",
            "action": "Upload actual progress, actual finish, remaining duration or forecast finish data before calculating delay and progress gap.",
        })
    productivity_summary = _workforce_productivity_summary(parsed)
    if productivity_summary.get("activities_with_shortage"):
        rows.append({
            "risk": "Workforce productivity shortage",
            "level": "High" if productivity_summary.get("max_delay_risk_days", 0) >= 5 else "Medium",
            "reason": f"{productivity_summary.get('activities_with_shortage')} activities require more workers than currently indicated.",
            "action": "Increase crews or extend activity duration based on productivity norms before confirming the schedule.",
        })
    if productivity_summary.get("needs_confirmation"):
        rows.append({
            "risk": "Productivity data confirmation",
            "level": "Medium",
            "reason": f"{productivity_summary.get('needs_confirmation')} activities need quantity, unit, duration, worker count or productivity confirmation.",
            "action": "Confirm activity units and productivity rates before using workforce planning results commercially.",
        })
    if any(s.detected_type == "procurement" for s in parsed.sheets):
        rows.append({
            "risk": "Procurement follow-up",
            "level": "Medium",
            "reason": "Procurement/material data was detected and requires schedule alignment.",
            "action": "Confirm supplier dates, long-lead materials and alternatives.",
        })
    if parsed.warnings:
        rows.append({
            "risk": "Data quality",
            "level": "Medium",
            "reason": "Some uploaded data could not be confidently mapped.",
            "action": "Ask the user to confirm unclear columns or upload a cleaner project-control file.",
        })
    if not rows:
        rows.append({
            "risk": "Data review required",
            "level": "Medium",
            "reason": "The uploaded files did not provide enough mapped KPI evidence for a full risk register.",
            "action": "Upload a plan/fact, cost or workforce file with clear headers.",
        })
    return rows


def build_actions(parsed: ParsedProjectData, risk: Dict[str, Any]) -> List[str]:
    actions: List[str] = []
    gap = risk.get("schedule_gap_percent")
    if gap is not None and gap > 0:
        actions.append("Track planned and actual execution weekly until the progress gap closes.")
        actions.append("Prepare a recovery schedule for delayed or critical activities.")
    if _actual_cost_needs_confirmation(parsed):
        actions.append("Confirm actual completed cost because the detected value exceeds the smeta/contract baseline.")
        actions.append("Review whether VAT, duplicate cumulative totals, or approved variation amounts are included in the detected actual cost.")
    if parsed.cost_variance_percent is not None:
        actions.append("Review cost variance by work package and separate approved changes from uncontrolled overruns.")
    if parsed.evidence.get("cost_actual_data_missing"):
        actions.append("Upload progress payment, invoice or confirmed actual cost data before calculating cost variance.")
    if parsed.evidence.get("schedule_actual_data_missing"):
        actions.append("Upload actual progress or forecast finish data before calculating schedule delay and plan/fact progress gap.")
    if parsed.workforce_current is not None and parsed.workforce_required and parsed.workforce_current < parsed.workforce_required:
        actions.append("Increase workforce on critical structural, finishing or MEP activities according to the recovery plan.")
    productivity_summary = _workforce_productivity_summary(parsed)
    if productivity_summary.get("activities_with_shortage"):
        actions.append("Review workforce productivity table and add crews to activities where required workers exceed actual workers.")
    if productivity_summary.get("max_delay_risk_days", 0):
        actions.append("Compare realistic duration against planned duration and revise the activity plan where delay risk is detected.")
    if parsed.warnings:
        actions.append("Confirm unclear column mappings before using the report for commercial decisions.")
    if not actions:
        actions.append("Upload a clearer cost, schedule, progress or workforce file to generate a stronger management dashboard.")
    return actions[:6]


def _clean_analysis_type(analysis_type: str | None) -> str:
    value = (analysis_type or "all").strip().lower().replace("-", "_")
    aliases = {
        "full": "all",
        "executive": "all",
        "dashboard": "all",
        "cost_analysis": "cost",
        "schedule_delay": "schedule",
        "planning": "schedule",
        "qrafik": "schedule",
        "manpower": "workforce",
        "labor": "workforce",
        "isci": "workforce",
        "progress_report": "progress",
        "material_continuity": "material",
        "procurement": "material",
        "materials": "material",
        "decision": "risk",
        "decisions": "risk",
        "risk_decisions": "risk",
        "f2": "progress",
        "f_2": "progress",
        "forma2": "progress",
    }
    value = aliases.get(value, value)
    return value if value in {"all", "cost", "schedule", "workforce", "progress", "material", "risk"} else "all"


def _dashboard_label(analysis_type: str) -> tuple[str, str]:
    labels = {
        "cost": (
            "Cost & Payment Control Dashboard",
            "Smeta baseline, progress payment evidence, actual completed cost, remaining value and payment risk are prioritized.",
        ),
        "schedule": (
            "Schedule Recovery Dashboard",
            "Schedule delay, actual progress, workforce gap and practical recovery actions are prioritized together.",
        ),
        "workforce": (
            "Workforce Productivity Dashboard",
            "Current manpower, required manpower, workforce gap and site mobilization risk are prioritized.",
        ),
        "progress": (
            "Progress Payment Dashboard",
            "Progress payment records, completed amount, actual execution percentage and remaining progress are prioritized.",
        ),
        "material": (
            "Material Continuity Dashboard",
            "Material stock, procurement status, delivery risk and continuity actions are prioritized.",
        ),
        "risk": (
            "Risk & Decisions Dashboard",
            "Risk register, decision prompts, open issues and recommended management actions are prioritized.",
        ),
        "all": (
            "Full Project Control Dashboard",
            "Schedule Recovery, Cost & Payment Control, Material Continuity, Risk & Decisions and data quality are consolidated for management review.",
        ),
    }
    return labels.get(analysis_type, labels["all"])


def _metric(label: str, value: Any, unit: str | None = None, status: str = "neutral", note: str | None = None) -> Dict[str, Any]:
    return {"label": label, "value": value, "unit": unit or "", "status": status, "note": note or ""}


def _is_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped in {"—", "-", "None", "null"}:
            return False
        low = stripped.lower()
        if low in {"not detected", "not available", "actual data required", "data required", "missing", "required"}:
            return False
    return True


def _is_meaningful_metric(metric: Dict[str, Any]) -> bool:
    return _is_meaningful_value(metric.get("value"))


def _filter_metrics(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [m for m in metrics if _is_meaningful_metric(m)]
    return filtered


def _row_has_evidence(row: Dict[str, Any]) -> bool:
    evidence_keys = ["planned", "actual", "remaining", "variance", "variance_value", "value", "quantity", "required", "current", "completed", "cumulative"]
    if any(_is_meaningful_value(row.get(k)) for k in evidence_keys):
        return True
    # Keep explicit management/evidence rows only when their status confirms useful information.
    status = str(row.get("status") or "").lower()
    if status in {"confirmed", "controlled", "baseline", "approved"}:
        return True
    return False


def _filter_panel(panel: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = panel.get("rows") or []
    filtered_rows = [r for r in rows if isinstance(r, dict) and (_is_meaningful_metric(r) or _row_has_evidence(r))]
    if not filtered_rows:
        return None
    new_panel = dict(panel)
    new_panel["rows"] = filtered_rows
    return new_panel


def _filter_panels(panels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for panel in panels:
        filtered = _filter_panel(panel)
        if filtered is not None:
            out.append(filtered)
    return out


def _visible_dashboard_blocks(parsed: ParsedProjectData, mode: str, risk: Dict[str, Any]) -> List[str]:
    profile = _adaptive_dashboard_profile(parsed, mode, risk)
    return list(profile.get("active_blocks") or [])


def _actual_cost_needs_confirmation(parsed: ParsedProjectData) -> bool:
    return bool(parsed.evidence.get("needs_confirmation_actual_cost") or parsed.evidence.get("commercial_guardrail"))


def _actual_cost_display(parsed: ParsedProjectData) -> Any:
    return "Needs confirmation" if _actual_cost_needs_confirmation(parsed) else parsed.actual_cost


def _actual_cost_status(parsed: ParsedProjectData) -> str:
    return "risk" if _actual_cost_needs_confirmation(parsed) else "primary"


def _actual_cost_note(parsed: ParsedProjectData) -> str:
    if not _actual_cost_needs_confirmation(parsed):
        return ""
    info = parsed.evidence.get("needs_confirmation_actual_cost") or {}
    ratio = info.get("ratio_percent")
    if ratio:
        return f"Detected amount is {ratio:g}% of smeta; confirm progress payment total or approved variation."
    return "Confirm progress payment total, VAT treatment or approved variation before commercial use."


def _cost_baseline(parsed: ParsedProjectData) -> Optional[float]:
    """Return the commercial baseline used for Cost & Payment Control.

    The uploaded smeta/cost-estimate value can arrive as either total_cost or
    planned_cost depending on the parser path. Cost dashboards must use one
    authoritative baseline consistently for remaining value and variance.
    """
    if parsed.total_cost is not None:
        return float(parsed.total_cost)
    if parsed.planned_cost is not None:
        return float(parsed.planned_cost)
    return None


def _remaining_cost(parsed: ParsedProjectData) -> Optional[float]:
    baseline = _cost_baseline(parsed)
    if baseline is None or parsed.actual_cost is None:
        return None
    return round(max(0.0, baseline - float(parsed.actual_cost)), 2)


def _cost_variance_value(parsed: ParsedProjectData) -> Optional[float]:
    baseline = _cost_baseline(parsed)
    if baseline is None or parsed.actual_cost is None:
        return None
    return round(float(parsed.actual_cost) - baseline, 2)


def _cost_control_rows(parsed: ParsedProjectData) -> List[Dict[str, Any]]:
    """Build clean Cost Estimate + Progress Payment control rows for result dashboard tables.

    These rows use explicit planned/actual/remaining/variance fields so the
    frontend does not have to infer table columns from generic metric rows.
    """
    baseline = _cost_baseline(parsed)
    actual = None if _actual_cost_needs_confirmation(parsed) else parsed.actual_cost
    remaining = _remaining_cost(parsed)
    variance_value = _cost_variance_value(parsed)
    variance_percent = parsed.cost_variance_percent
    has_actual = actual is not None
    rows: List[Dict[str, Any]] = [
        {
            "work_package": "Cost Estimate / Smeta baseline",
            "planned": baseline,
            "actual": None,
            "remaining": None,
            "variance": None,
            "status": "Baseline",
            "note": "Approved smeta / contract baseline used for comparison.",
        },
        {
            "work_package": "Progress Payment / actual confirmed cost",
            "planned": None,
            "actual": _actual_cost_display(parsed),
            "remaining": None,
            "variance": None,
            "status": "Confirmed" if has_actual else ("Needs confirmation" if _actual_cost_needs_confirmation(parsed) else "Actual data required"),
            "note": _actual_cost_note(parsed) or "Cumulative progress payment value detected from uploaded files.",
        },
        {
            "work_package": "Cost & Payment summary",
            "planned": baseline,
            "actual": actual,
            "remaining": remaining,
            "variance": variance_percent,
            "variance_value": variance_value,
            "status": "Controlled" if has_actual and variance_percent is not None and variance_percent <= 0 else ("Review" if has_actual else "Actual data required"),
            "note": "Remaining value = smeta baseline minus confirmed progress payment / actual cost.",
        },
        {
            "work_package": "Payment evidence",
            "planned": None,
            "actual": "Progress payment records" if _has_progress_payment_source(parsed) else "Not detected",
            "remaining": None,
            "variance": None,
            "status": "Confirmed" if _has_progress_payment_source(parsed) else "Required",
            "note": "Use confirmed progress payment data for commercial decisions.",
        },
    ]
    return rows


def _workforce_gap(parsed: ParsedProjectData) -> Optional[int]:
    if parsed.workforce_current is None or parsed.workforce_required is None:
        return None
    return int(parsed.workforce_current) - int(parsed.workforce_required)


def _workforce_productivity(parsed: ParsedProjectData) -> Dict[str, Any]:
    return (parsed.evidence or {}).get("workforce_productivity") or {}


def _workforce_productivity_summary(parsed: ParsedProjectData) -> Dict[str, Any]:
    return _workforce_productivity(parsed).get("summary") or {}


def _workforce_productivity_activities(parsed: ParsedProjectData) -> List[Dict[str, Any]]:
    return _workforce_productivity(parsed).get("activities") or []


def _available_sheet_count(parsed: ParsedProjectData, detected_type: str) -> int:
    return sum(1 for s in parsed.sheets if s.detected_type == detected_type)




def _confidence_breakdown(parsed: ParsedProjectData, risk: Dict[str, Any], confidence: int) -> Dict[str, Any]:
    positives: List[str] = []
    gaps: List[str] = []
    if parsed.project_name:
        positives.append("Project name detected")
    else:
        gaps.append("Project name not clearly detected")
    if parsed.currency:
        positives.append("Currency detected")
    else:
        gaps.append("Currency not clearly detected")
    if parsed.total_cost is not None or parsed.planned_cost is not None:
        positives.append("Cost estimate / smeta baseline detected")
    else:
        gaps.append("Cost estimate / smeta baseline missing")
    if _has_progress_payment_source(parsed):
        positives.append("Progress payment / actual cost evidence detected")
    else:
        gaps.append("Progress payment / actual cost evidence missing")
    if parsed.planned_execution is not None or parsed.baseline_finish is not None:
        positives.append("Baseline schedule/progress evidence detected")
    else:
        gaps.append("Baseline schedule/progress evidence missing")
    if parsed.actual_execution is not None or parsed.estimated_finish is not None:
        positives.append("Actual progress / forecast evidence detected")
    else:
        gaps.append("Actual progress / forecast evidence missing")
    if parsed.workforce_current is not None or parsed.workforce_required is not None:
        positives.append("Workforce evidence detected")
    else:
        gaps.append("Workforce evidence missing")
    if any(s.detected_type in {"procurement", "material"} for s in parsed.sheets):
        positives.append("Material/procurement evidence detected")
    else:
        gaps.append("Material/procurement evidence missing")
    if parsed.sheets:
        positives.append(f"{len(parsed.sheets)} sheet profile(s) detected")
    else:
        gaps.append("No sheet profile detected")
    if parsed.warnings:
        gaps.append("Some uploaded data needs confirmation")
    return {"score": confidence, "level": "High" if confidence >= 85 else "Medium" if confidence >= 65 else "Low" if confidence >= 40 else "Insufficient", "positive_evidence": positives[:8], "missing_or_weak_evidence": gaps[:8]}


def _missing_data_for_mode(parsed: ParsedProjectData, mode: str) -> List[Dict[str, str]]:
    mode = _clean_analysis_type(mode)
    items: List[Dict[str, str]] = []
    def add(field: str, why: str, priority: str = "Required") -> None:
        items.append({"field": field, "why": why, "priority": priority})
    if mode in {"all", "cost", "progress"}:
        if _cost_baseline(parsed) is None:
            add("Cost estimate / smeta baseline", "Needed to compare approved budget, remaining value and variance.")
        if not _has_progress_payment_source(parsed):
            add("Progress payment / F-2 or actual cost", "Needed to confirm actual completed value and payment exposure.")
        if parsed.evidence.get("cost_actual_data_missing"):
            add("Confirmed actual cost source", "Cost variance is held until progress payment / actual cost data is uploaded.")
    if mode in {"all", "schedule"}:
        if parsed.planned_execution is None and parsed.baseline_finish is None:
            add("Baseline schedule or planned progress", "Needed to calculate schedule gap and delay baseline.")
        if parsed.actual_execution is None and parsed.estimated_finish is None:
            add("Actual progress or forecast finish", "Needed to calculate recovery requirement and delay impact.")
    if mode in {"all", "schedule", "workforce"}:
        if parsed.workforce_current is None:
            add("Current workforce / manpower", "Needed to calculate crew shortage and recovery capacity.")
        if parsed.workforce_required is None and not _workforce_productivity_summary(parsed).get("total_required_workers"):
            add("Required workforce or productivity basis", "Needed to estimate manpower gap and realistic duration.", "Recommended")
    if mode in {"all", "material"} and not any(s.detected_type in {"procurement", "material"} for s in parsed.sheets):
        add("Material stock and delivery schedule", "Needed to detect stock-out date, procurement delay and continuity risk.")
    if mode in {"all", "risk"} and not items:
        add("Risk / issue log or management notes", "Improves decision prompts, owners, deadlines and consequence tracking.", "Recommended")
    return items[:10]


def _audit_trail(parsed: ParsedProjectData) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sheet in parsed.sheets[:10]:
        mapped = sheet.mapped_columns or {}
        mapped_list = ", ".join(f"{k}: {v}" for k, v in mapped.items()) if mapped else "No mapped columns"
        rows.append({
            "source": sheet.sheet_name,
            "type": sheet.detected_type,
            "confidence": sheet.confidence,
            "evidence": mapped_list,
        })
    if not rows:
        rows.append({"source": "Uploaded files", "type": "not detected", "confidence": 0, "evidence": "No sheet profile available"})
    return rows


def _how_calculated(parsed: ParsedProjectData, risk: Dict[str, Any], mode: str) -> List[Dict[str, str]]:
    mode = _clean_analysis_type(mode)
    rows: List[Dict[str, str]] = []
    if mode in {"all", "cost", "progress"}:
        rows.append({"metric": "Remaining value", "formula": "Cost Estimate / Smeta - Confirmed Progress Payment", "example": f"{_cost_baseline(parsed) or '—'} - {parsed.actual_cost or '—'} = {_remaining_cost(parsed) if _remaining_cost(parsed) is not None else '—'}"})
        rows.append({"metric": "Cost variance %", "formula": "(Actual confirmed cost - Smeta baseline) / Smeta baseline × 100", "example": f"{parsed.cost_variance_percent if parsed.cost_variance_percent is not None else '—'}%"})
    if mode in {"all", "schedule"}:
        rows.append({"metric": "Progress gap", "formula": "Planned progress - Actual progress", "example": f"{risk.get('schedule_gap_percent') if risk.get('schedule_gap_percent') is not None else '—'}%"})
        rows.append({"metric": "Delay impact", "formula": "Estimated/forecast finish - baseline finish", "example": f"{parsed.delay_days if parsed.delay_days is not None else '—'} days"})
    if mode in {"all", "schedule", "workforce"}:
        rows.append({"metric": "Workforce gap", "formula": "Current workforce - Required workforce", "example": f"{_workforce_gap(parsed) if _workforce_gap(parsed) is not None else '—'} workers"})
    if mode in {"all", "risk"}:
        rows.append({"metric": "Risk score", "formula": "Weighted schedule, cost, labor, procurement and quality risk components", "example": f"{risk.get('score') if risk.get('score') is not None else '—'}/100"})
    rows.append({"metric": "Statistical analytics", "formula": "Mean, median, standard deviation, coefficient of variation, trend, correlation and outlier checks are calculated from detected numeric evidence.", "example": "Shown when enough numeric data is available."})
    return rows[:10]


def _what_if_scenarios(parsed: ParsedProjectData, risk: Dict[str, Any], mode: str) -> List[Dict[str, Any]]:
    mode = _clean_analysis_type(mode)
    rows: List[Dict[str, Any]] = []
    gap = risk.get("schedule_gap_percent")
    if mode in {"all", "schedule"}:
        if parsed.workforce_current is not None and parsed.workforce_required is not None and parsed.workforce_required > parsed.workforce_current:
            shortage = parsed.workforce_required - parsed.workforce_current
            rows.append({"scenario": "Current pace", "impact": f"Workforce remains {shortage} below requirement", "decision": "Expect recovery pressure unless scope, productivity or duration changes."})
            rows.append({"scenario": "Recovery crew", "impact": f"Add approximately {shortage} workers to meet indicated requirement", "decision": "Prioritize critical path crews and weekly plan/fact monitoring."})
        elif gap:
            rows.append({"scenario": "Progress recovery", "impact": f"Progress gap is {gap}%", "decision": "Prepare short interval recovery plan and confirm weekly production targets."})
    if mode in {"all", "cost"}:
        remaining = _remaining_cost(parsed)
        if remaining is not None:
            rows.append({"scenario": "No additional approved changes", "impact": f"Remaining commercial buffer is {remaining:,.2f} {parsed.currency or 'AZN'}", "decision": "Control new works through approved variation orders before execution."})
        if parsed.cost_variance_percent is not None and parsed.cost_variance_percent > 0:
            rows.append({"scenario": "Current cost trend continues", "impact": f"Cost is {parsed.cost_variance_percent:g}% above baseline", "decision": "Freeze unsupported overruns and review work-package variances."})
    if mode in {"all", "material"}:
        rows.append({"scenario": "Delivery delay", "impact": "Long-lead material delay may affect critical activities", "decision": "Confirm supplier delivery dates, stock levels and alternatives."})
    if not rows:
        rows.append({"scenario": "Data completion", "impact": "What-if scenarios need clearer plan/fact, cost, workforce or material data", "decision": "Upload the missing template fields shown in the data readiness panel."})
    return rows[:6]


def _action_owner(action: str, mode: str) -> str:
    """Assign action owner semantically, never by row order."""
    lower = (action or "").lower()
    if any(w in lower for w in ["cost", "payment", "f-2", "progress payment", "variation", "commercial", "smeta", "budget", "completed cost", "actual cost"]):
        return "Commercial/QS"
    if any(w in lower for w in ["material", "supplier", "delivery", "procurement", "stock", "lead time"]):
        return "Procurement"
    if any(w in lower for w in ["workforce", "crew", "manpower", "site", "mobilization", "mobilise", "increase workers"]):
        return "Site Team"
    if any(w in lower for w in ["decision", "approve", "approval", "risk", "management", "contract", "claim"]):
        return "Management"
    if any(w in lower for w in ["schedule", "delay", "progress", "recovery", "baseline", "forecast", "plan/fact"]):
        return "Project Control"
    mode = _clean_analysis_type(mode)
    if mode == "cost":
        return "Commercial/QS"
    if mode == "material":
        return "Procurement"
    if mode == "schedule":
        return "Project Control"
    if mode == "risk":
        return "Management"
    return "Project Control"


def _action_tracker(parsed: ParsedProjectData, risk: Dict[str, Any], mode: str) -> List[Dict[str, str]]:
    actions = build_actions(parsed, risk)
    rows = []
    for action in actions[:6]:
        lower = action.lower()
        owner = _action_owner(action, mode)
        urgency = "High" if any(w in lower for w in ["confirm", "increase", "recovery", "freeze", "approve", "critical"]) else "Medium"
        rows.append({"action": action, "owner": owner, "deadline": "3-7 days" if urgency == "High" else "Next control cycle", "status": "Open", "priority": urgency})
    return rows



def _adaptive_dashboard_profile(parsed: ParsedProjectData, mode: str, risk: Dict[str, Any]) -> Dict[str, Any]:
    """Describe which dashboard blocks can be shown confidently from the uploaded data.

    Customers upload very different file structures. This profile lets the
    frontend/report behave flexibly: strong blocks are shown as active, weak
    blocks are marked as optional/missing instead of forcing a fixed dashboard.
    """
    mode = _clean_analysis_type(mode)
    capabilities = {
        "cost_payment": bool(_cost_baseline(parsed) is not None or _has_progress_payment_source(parsed) or parsed.actual_cost is not None),
        "schedule_recovery": bool(parsed.planned_execution is not None or parsed.actual_execution is not None or parsed.baseline_finish or parsed.estimated_finish or any(s.detected_type == "schedule" for s in parsed.sheets)),
        "workforce": bool(parsed.workforce_current is not None or parsed.workforce_required is not None or _workforce_productivity_summary(parsed).get("activities_checked")),
        "material_continuity": bool(any(s.detected_type in {"procurement", "material"} for s in parsed.sheets)),
        "risk_decisions": bool(parsed.warnings or risk.get("score") is not None or len(build_risk_register(parsed, risk)) > 0),
        "statistical_analytics": bool(parsed.sheets or parsed.total_cost is not None or parsed.actual_cost is not None or parsed.actual_execution is not None),
    }
    package_requirements = {
        "cost": ["cost_payment", "statistical_analytics", "risk_decisions"],
        "schedule": ["schedule_recovery", "workforce", "risk_decisions"],
        "material": ["material_continuity", "schedule_recovery", "risk_decisions"],
        "risk": ["risk_decisions", "cost_payment", "schedule_recovery", "material_continuity"],
        "all": ["cost_payment", "schedule_recovery", "workforce", "material_continuity", "risk_decisions", "statistical_analytics"],
    }
    required = package_requirements.get(mode, package_requirements["all"])
    active = [k for k in required if capabilities.get(k)]
    missing = [k for k in required if not capabilities.get(k)]
    if not active:
        active = [k for k, v in capabilities.items() if v]
    return {
        "mode": mode,
        "active_blocks": active,
        "missing_blocks": missing,
        "capabilities": capabilities,
        "layout": "adaptive",
        "message": "Dashboard blocks are generated from available uploaded evidence. Missing blocks are shown as data requirements, not invented results.",
    }

def _advanced_sections(parsed: ParsedProjectData, risk: Dict[str, Any], confidence: int, mode: str) -> Dict[str, Any]:
    statistical = build_statistical_analytics(parsed, risk, mode)
    return {
        "data_readiness": _confidence_breakdown(parsed, risk, confidence),
        "missing_data": _missing_data_for_mode(parsed, mode),
        "audit_trail": _audit_trail(parsed),
        "how_calculated": _how_calculated(parsed, risk, mode),
        "what_if": _what_if_scenarios(parsed, risk, mode),
        "action_tracker": _action_tracker(parsed, risk, mode),
        "statistical_analytics": statistical,
        "adaptive_dashboard": _adaptive_dashboard_profile(parsed, mode, risk),
    }

def build_analysis_dashboard_sections(parsed: ParsedProjectData, risk: Dict[str, Any], confidence: int, analysis_type: str) -> Dict[str, Any]:
    """Build a dashboard payload that the frontend and PDF use for analysis-specific views.

    The generic KPI layer remains available, but this object tells the frontend/PDF which
    dashboard should be rendered for the user's selected analysis mode.
    """
    t = _clean_analysis_type(analysis_type)
    currency = parsed.currency or "AZN"
    remaining = _remaining_cost(parsed)
    workforce_gap = _workforce_gap(parsed)
    progress_gap = risk.get("schedule_gap_percent")
    cost_sheets = _available_sheet_count(parsed, "cost")
    progress_sheets = _available_sheet_count(parsed, "progress")
    schedule_sheets = _available_sheet_count(parsed, "schedule")
    workforce_sheets = _available_sheet_count(parsed, "workforce")

    common_panels = [
        {
            "title": "Data confidence",
            "rows": [
                _metric("Dashboard confidence", confidence, "/100"),
                _metric("Detected sheets", len(parsed.sheets)),
                _metric("Cost sheets", cost_sheets),
                _metric("Progress sheets", progress_sheets),
            ],
        }
    ]

    if t == "material":
        material_count = _available_sheet_count(parsed, "procurement") + _available_sheet_count(parsed, "material")
        if material_count:
            parts.append(f"Material/procurement evidence was detected in {material_count} sheet(s).")
        else:
            parts.append("Material continuity data was not clearly detected from the uploaded files.")
        parts.append("Confirm stock levels, supplier delivery dates, critical materials and alternative procurement actions before using continuity conclusions.")
        parts.append(f"Dashboard confidence is {confidence}/100 based on detected sheets, mapped columns and extracted KPI evidence.")
        return " ".join(parts)
    if t == "risk":
        register = build_risk_register(parsed, risk)
        if risk.get("score") is not None:
            parts.append(f"Combined risk score is {risk.get('score')}/100 with {risk.get('level')} status.")
        parts.append(f"Risk & Decisions dashboard prepared {len(register)} risk/decision item(s) from available evidence.")
        parts.append("Use the recommended actions as management prompts and confirm unclear source data before final decisions.")
        parts.append(f"Dashboard confidence is {confidence}/100 based on detected sheets, mapped columns and extracted KPI evidence.")
        return " ".join(parts)

    if t == "cost":
        baseline = _cost_baseline(parsed)
        variance_value = _cost_variance_value(parsed)
        primary = [
            _metric("Cost Estimate / Smeta", baseline, currency, "primary", "Approved baseline / cost estimate"),
            _metric("Actual confirmed Progress Payment", _actual_cost_display(parsed), currency if not _actual_cost_needs_confirmation(parsed) else "", _actual_cost_status(parsed), _actual_cost_note(parsed) or "Confirmed actual / progress payment value"),
            _metric("Remaining value", remaining, currency, "neutral", "Baseline minus confirmed progress payment"),
            _metric("Cost variance", parsed.cost_variance_percent, "%", "risk" if parsed.cost_variance_percent and parsed.cost_variance_percent > 0 else "neutral", "Against smeta baseline"),
            _metric("Variance amount", variance_value, currency, "risk" if variance_value and variance_value > 0 else "neutral", "Actual progress payment minus baseline"),
            _metric("Commercial risk", risk.get("level"), "", "risk" if risk.get("score") and risk.get("score") >= 40 else "neutral", "Cost guardrails and mapping confidence"),
        ]
        panels = [
            {
                "title": "Cost & Progress Payment summary",
                "rows": _cost_control_rows(parsed),
            },
            {
                "title": "Cost control notes",
                "rows": [
                    _metric("Variance available", "Yes" if parsed.cost_variance_percent is not None else "No"),
                    _metric("Remaining value formula", "Cost Estimate / Smeta - Actual confirmed Progress Payment"),
                    _metric("Recommended check", "Separate approved changes from uncontrolled overruns"),
                ],
            },
        ] + common_panels
    elif t == "schedule":
        productivity_summary = _workforce_productivity_summary(parsed)
        recovery_shortage = productivity_summary.get("activities_with_shortage")
        max_delay = productivity_summary.get("max_delay_risk_days")
        primary = [
            _metric("Planned progress", parsed.planned_execution, "%", "primary"),
            _metric("Actual progress", parsed.actual_execution, "%", "primary"),
            _metric("Progress gap", progress_gap, "%", "risk" if progress_gap else "neutral"),
            _metric("Delay impact", parsed.delay_days, "days", "risk" if parsed.delay_days else "neutral"),
            _metric("Required workforce", productivity_summary.get("total_required_workers") or parsed.workforce_required, "workers", "primary"),
            _metric("Actual workforce", productivity_summary.get("total_actual_workers") or parsed.workforce_current, "workers", "primary"),
        ]
        panels = [
            {
                "title": "Schedule baseline",
                "rows": [
                    _metric("Baseline finish", parsed.baseline_finish),
                    _metric("Estimated finish", parsed.estimated_finish),
                    _metric("Schedule sheets", schedule_sheets),
                    _metric("Actual schedule data", "Missing actual progress / forecast" if parsed.evidence.get("schedule_actual_data_missing") else ("Required" if not parsed.baseline_finish or not parsed.estimated_finish else "Confirmed")),
                ],
            },
            {
                "title": "Recovery resources",
                "rows": [
                    _metric("Workforce sheets", workforce_sheets),
                    _metric("Workforce gap", workforce_gap, "workers", "risk" if workforce_gap and workforce_gap < 0 else "neutral"),
                    _metric("Activities with shortage", recovery_shortage, "activities", "risk" if recovery_shortage else "neutral"),
                    _metric("Max delay risk", max_delay, "days", "risk" if max_delay else "neutral"),
                    _metric("Recovery action", "Connect weekly plan/fact updates with crew mobilization and critical activity recovery."),
                ],
            },
        ] + common_panels
    elif t == "workforce":
        productivity = _workforce_productivity(parsed)
        productivity_summary = productivity.get("summary") or {}
        activities = productivity.get("activities") or []
        productivity_rows = []
        for item in activities[:8]:
            label = item.get("activity_label_en") or item.get("activity_name")
            productivity_rows.extend([
                _metric(f"{label} — required", item.get("required_workers"), "workers", "risk" if (item.get("workforce_gap") or 0) < 0 else "neutral", item.get("risk_level")),
                _metric(f"{label} — realistic duration", item.get("realistic_days"), "days", "risk" if (item.get("delay_risk_days") or 0) > 0 else "neutral", f"plan {item.get('planned_days') or 'n/a'} days"),
            ])
        if not productivity_rows:
            productivity_rows = [
                _metric("Activity productivity rows", "Not detected"),
                _metric("Required data", "Activity + quantity + unit + planned duration + actual workers"),
            ]
        primary = [
            _metric("Activities checked", productivity_summary.get("activities_checked"), "activities", "primary"),
            _metric("Required workforce", productivity_summary.get("total_required_workers") or parsed.workforce_required, "workers", "primary"),
            _metric("Actual workforce", productivity_summary.get("total_actual_workers") or parsed.workforce_current, "workers", "primary"),
            _metric("Max delay risk", productivity_summary.get("max_delay_risk_days"), "days", "risk" if productivity_summary.get("max_delay_risk_days") else "neutral"),
        ]
        panels = [
            {
                "title": "Productivity planning",
                "rows": [
                    _metric("Calculated activities", productivity_summary.get("calculated_activities")),
                    _metric("Activities with shortage", productivity_summary.get("activities_with_shortage"), "activities", "risk" if productivity_summary.get("activities_with_shortage") else "neutral"),
                    _metric("Needs confirmation", productivity_summary.get("needs_confirmation"), "activities", "risk" if productivity_summary.get("needs_confirmation") else "neutral"),
                    _metric("Library version", productivity.get("library_version") or "Not used"),
                ],
            },
            {
                "title": "Activity workforce requirements",
                "rows": productivity_rows,
            },
            {
                "title": "Resource logic",
                "rows": [
                    _metric("Formula", "Required workers = quantity / (productivity × planned days)"),
                    _metric("Realistic duration", "quantity / (actual workers × productivity)"),
                    _metric("Recommended check", "Confirm activity units and productivity rates before final schedule decisions"),
                ],
            },
        ] + common_panels
    elif t == "material":
        material_sheets = _available_sheet_count(parsed, "procurement") + _available_sheet_count(parsed, "material")
        primary = [
            _metric("Procurement sheets", material_sheets, "sheets", "primary" if material_sheets else "neutral"),
            _metric("Material continuity risk", risk.get("components", {}).get("procurement") if isinstance(risk.get("components"), dict) else risk.get("score"), "/100", "risk" if material_sheets else "neutral"),
            _metric("Delivery confirmation", "Required" if material_sheets else "Not detected", "", "risk" if material_sheets else "neutral"),
            _metric("Recommended action", "Confirm stock, delivery dates and long-lead materials"),
        ]
        panels = [
            {
                "title": "Material continuity evidence",
                "rows": [
                    _metric("Procurement sheets", material_sheets),
                    _metric("Supplier / delivery data", "Detected" if material_sheets else "Not detected"),
                    _metric("Continuity check", "Confirm critical materials, delivery dates and alternatives"),
                    _metric("Decision need", "Escalate shortages affecting critical path"),
                ],
            }
        ] + common_panels
    elif t == "risk":
        register = build_risk_register(parsed, risk)
        primary = [
            _metric("Risk score", risk.get("score"), "/100", "risk"),
            _metric("Risk level", risk.get("level"), "", "risk" if risk.get("score") and risk.get("score") >= 40 else "neutral"),
            _metric("Open risks", len(register), "risks", "primary"),
            _metric("Decision focus", "Management actions", "", "primary"),
        ]
        panels = [
            {
                "title": "Risk and decision register",
                "rows": [
                    _metric(item.get("risk"), item.get("level"), "", "risk", item.get("action")) for item in register[:8]
                ] or [_metric("Data review required", "Upload cost, schedule, material or site records")],
            }
        ] + common_panels
    elif t == "progress":
        primary = [
            _metric("Actual execution", parsed.actual_execution, "%", "primary"),
            _metric("Completed amount", _actual_cost_display(parsed), currency if not _actual_cost_needs_confirmation(parsed) else "", _actual_cost_status(parsed), _actual_cost_note(parsed)),
            _metric("Smeta baseline", parsed.total_cost, currency),
            _metric("Progress sheets", progress_sheets),
        ]
        panels = [
            {
                "title": "Progress payment basis",
                "rows": [
                    _metric("Progress payment sheets detected", progress_sheets),
                    _metric("Progress calculation", "completed amount / smeta baseline"),
                    _metric("Planned progress", parsed.planned_execution, "%"),
                    _metric("Progress gap", progress_gap, "%"),
                ],
            }
        ] + common_panels
    else:
        primary = [
            _metric("Actual execution", parsed.actual_execution, "%", "primary"),
            _metric("Total cost", parsed.total_cost, currency, "primary"),
            _metric("Delay", parsed.delay_days, "days", "risk" if parsed.delay_days else "neutral"),
            _metric("Risk score", risk.get("score"), "/100", "risk"),
        ]
        panels = [
            {
                "title": "Executive control summary",
                "rows": [
                    _metric("Cost sheets", cost_sheets),
                    _metric("Progress sheets", progress_sheets),
                    _metric("Schedule sheets", schedule_sheets),
                    _metric("Workforce sheets", workforce_sheets),
                    _metric("Productivity activities", _workforce_productivity_summary(parsed).get("activities_checked")),
                    _metric("Workforce shortages", _workforce_productivity_summary(parsed).get("activities_with_shortage")),
                ],
            }
        ] + common_panels

    primary = _filter_metrics(primary)
    panels = _filter_panels(panels)
    advanced_sections = _advanced_sections(parsed, risk, confidence, t)
    visible_blocks = _visible_dashboard_blocks(parsed, t, risk)
    suppressed_blocks = (advanced_sections.get("adaptive_dashboard") or {}).get("missing_blocks") or []
    title, description = _dashboard_label(t)
    return {
        "mode": t,
        "title": title,
        "description": description,
        "primary_kpis": primary,
        "panels": panels,
<<<<<<< HEAD
        "cost_rows": [r for r in (_cost_control_rows(parsed) if t == "cost" else []) if _row_has_evidence(r)],
        "visible_blocks": visible_blocks,
        "suppressed_empty_blocks": suppressed_blocks,
        "advanced_sections": advanced_sections,
        "adaptive_policy": "Package-specific dashboard blocks are rendered only when uploaded data provides enough evidence. Empty modules are converted into missing-data guidance instead of blank cards.",
=======
        "cost_rows": _cost_control_rows(parsed) if t == "cost" else [],
>>>>>>> a71c3ae48045c65514ab1d10b3c6e7f098eb1be3
        "pdf_logic": "The PDF report is generated from the same analysis-specific dashboard payload shown on the result page.",
    }


def build_dashboard(project_id: str, parsed: ParsedProjectData, analysis_type: str | None = "all") -> Dict[str, Any]:
    analysis_type = _clean_analysis_type(analysis_type)
    apply_baseline_actual_guardrails(parsed, analysis_type)
    risk = compute_risk(parsed)
    confidence = confidence_score(parsed, risk)
    status = _status_from_score(risk["score"])
    today = date.today().isoformat()
    # Every generated dashboard/export must have its own immutable result ID.
    # Do not reuse only project_id suffix, because the same uploaded project can be
    # re-analysed several times with different packages or manual mappings.
    result_id = f"DBR-{date.today().year}-{uuid4().hex[:8].upper()}"
    report_id = result_id

    dashboard_sections = build_analysis_dashboard_sections(parsed, risk, confidence, analysis_type)
    dashboard = {
        "project": {
            "name": parsed.project_name or "DevBareun Uploaded Project",
            "report_id": report_id,
            "result_id": result_id,
            "report_date": today,
            "status": status,
            "currency": parsed.currency or "Not detected",
            "confidence": confidence,
            "analysis_type": analysis_type,
            "dashboard_title": dashboard_sections.get("title"),
            "dashboard_description": dashboard_sections.get("description"),
        },
        "kpis": {
            "planned_execution": _round(parsed.planned_execution),
            "actual_execution": _round(parsed.actual_execution),
            "schedule_gap_percent": risk.get("schedule_gap_percent"),
            "delay_days": parsed.delay_days,
            "total_cost": _round(parsed.total_cost, 2),
            "planned_cost": _round(parsed.planned_cost, 2),
            "actual_cost": _round(parsed.actual_cost, 2),
            "remaining_cost": _round(_remaining_cost(parsed), 2),
            "cost_variance_amount": _round(_cost_variance_value(parsed), 2),
            "cost_variance_percent": _round(parsed.cost_variance_percent),
            "workforce_current": parsed.workforce_current,
            "workforce_required": parsed.workforce_required,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "currency": parsed.currency,
        },
        "forecast": {
            "baseline_finish": parsed.baseline_finish,
            "estimated_finish": parsed.estimated_finish,
            "delay_impact_days": parsed.delay_days,
        },
        "risk_components": risk["components"],
        "dashboard_sections": dashboard_sections,
        "executive_summary": build_summary(parsed, risk, confidence, analysis_type),
        "risk_register": build_risk_register(parsed, risk),
        "recommended_actions": build_actions(parsed, risk),
        "data_quality": {
            "confidence": confidence,
            "readiness": dashboard_sections.get("advanced_sections", {}).get("data_readiness"),
            "missing_data": dashboard_sections.get("advanced_sections", {}).get("missing_data"),
            "audit_trail": dashboard_sections.get("advanced_sections", {}).get("audit_trail"),
            "statistical_analytics": dashboard_sections.get("advanced_sections", {}).get("statistical_analytics"),
            "warnings": parsed.warnings,
            "sheet_profiles": [s.to_dict() for s in parsed.sheets],
        },
        "raw_extracted": parsed.to_dict(),
    }
    return {"project_id": project_id, "dashboard": dashboard}
