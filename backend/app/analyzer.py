from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import ParsedProjectData


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
            msg = "Actual cost / F-2 / progress payment data was not found. Cost variance and actual execution require confirmed actual data."
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


def build_summary(parsed: ParsedProjectData, risk: Dict[str, Any], confidence: int) -> str:
    parts: List[str] = []
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
            parts.append("Actual cost, F-2 or progress payment data was not confirmed, so cost variance and actual execution are not calculated.")

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
            "action": "Confirm the correct F-2 cumulative total, VAT treatment, duplicate totals or approved variation before using this value commercially.",
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
            "reason": "Cost estimate / smeta data was detected, but no confirmed actual cost, F-2 or progress payment source was found.",
            "action": "Upload F-2, interim payment, invoice or confirmed actual cost data before calculating cost variance or actual execution.",
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
        actions.append("Upload F-2, interim payment, invoice or confirmed actual cost data before calculating cost variance.")
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
        "f2": "progress",
        "f_2": "progress",
        "forma2": "progress",
    }
    value = aliases.get(value, value)
    return value if value in {"all", "cost", "schedule", "workforce", "progress"} else "all"


def _dashboard_label(analysis_type: str) -> tuple[str, str]:
    labels = {
        "cost": (
            "Cost & Payment Control Dashboard",
            "Smeta baseline, F-2/progress payment evidence, actual completed cost, remaining value and payment risk are prioritized.",
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
            "Progress / F-2 Dashboard",
            "F-2 certificates, completed amount, actual execution percentage and remaining progress are prioritized.",
        ),
        "all": (
            "Full Project Control Dashboard",
            "Schedule Recovery, Cost & Payment Control, workforce, risk and data quality are consolidated for management review.",
        ),
    }
    return labels.get(analysis_type, labels["all"])


def _metric(label: str, value: Any, unit: str | None = None, status: str = "neutral", note: str | None = None) -> Dict[str, Any]:
    return {"label": label, "value": value, "unit": unit or "", "status": status, "note": note or ""}


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
        return f"Detected amount is {ratio:g}% of smeta; confirm F-2 total or approved variation."
    return "Confirm F-2 total, VAT treatment or approved variation before commercial use."


def _remaining_cost(parsed: ParsedProjectData) -> Optional[float]:
    if parsed.total_cost is None or parsed.actual_cost is None:
        return None
    return round(max(0.0, float(parsed.total_cost) - float(parsed.actual_cost)), 2)


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

    if t == "cost":
        primary = [
            _metric("Smeta / contract total", parsed.total_cost, currency, "primary"),
            _metric("Actual completed cost", _actual_cost_display(parsed), currency if not _actual_cost_needs_confirmation(parsed) else "", _actual_cost_status(parsed), _actual_cost_note(parsed)),
            _metric("Remaining value", remaining, currency),
            _metric("Cost variance", parsed.cost_variance_percent, "%", "risk" if parsed.cost_variance_percent else "neutral"),
        ]
        panels = [
            {
                "title": "Commercial baseline",
                "rows": [
                    _metric("Planned cost", parsed.planned_cost, currency),
                    _metric("Total cost / smeta", parsed.total_cost, currency),
                    _metric("Actual cost source", "Missing actual data" if parsed.evidence.get("cost_actual_data_missing") else ("Needs confirmation" if _actual_cost_needs_confirmation(parsed) else ("F-2 / progress certificates" if progress_sheets else "Not detected"))),
                ],
            },
            {
                "title": "Cost control notes",
                "rows": [
                    _metric("Variance available", "Yes" if parsed.cost_variance_percent is not None else "No"),
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
    elif t == "progress":
        primary = [
            _metric("Actual execution", parsed.actual_execution, "%", "primary"),
            _metric("Completed amount", _actual_cost_display(parsed), currency if not _actual_cost_needs_confirmation(parsed) else "", _actual_cost_status(parsed), _actual_cost_note(parsed)),
            _metric("Smeta baseline", parsed.total_cost, currency),
            _metric("Progress sheets", progress_sheets),
        ]
        panels = [
            {
                "title": "F-2 / progress basis",
                "rows": [
                    _metric("F-2 sheets detected", progress_sheets),
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

    title, description = _dashboard_label(t)
    return {
        "mode": t,
        "title": title,
        "description": description,
        "primary_kpis": primary,
        "panels": panels,
        "pdf_logic": "The PDF report is generated from the same analysis-specific dashboard payload shown on the result page.",
    }


def build_dashboard(project_id: str, parsed: ParsedProjectData, analysis_type: str | None = "all") -> Dict[str, Any]:
    analysis_type = _clean_analysis_type(analysis_type)
    apply_baseline_actual_guardrails(parsed, analysis_type)
    risk = compute_risk(parsed)
    confidence = confidence_score(parsed, risk)
    status = _status_from_score(risk["score"])
    today = date.today().isoformat()
    report_id = f"DBR-{date.today().year}-{project_id[-6:].upper()}"

    dashboard_sections = build_analysis_dashboard_sections(parsed, risk, confidence, analysis_type)
    dashboard = {
        "project": {
            "name": parsed.project_name or "DevBareun Uploaded Project",
            "report_id": report_id,
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
        "executive_summary": build_summary(parsed, risk, confidence),
        "risk_register": build_risk_register(parsed, risk),
        "recommended_actions": build_actions(parsed, risk),
        "data_quality": {
            "confidence": confidence,
            "warnings": parsed.warnings,
            "sheet_profiles": [s.to_dict() for s in parsed.sheets],
        },
        "raw_extracted": parsed.to_dict(),
    }
    return {"project_id": project_id, "dashboard": dashboard}
