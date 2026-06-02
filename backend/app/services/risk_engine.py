from __future__ import annotations

from typing import Any, Dict, List


SEVERITY_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def generate_risk_register(normalized: Dict[str, Any], analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
    metrics = analytics.get("metrics") or {}
    warnings = normalized.get("warnings") or []
    risks: List[Dict[str, Any]] = []

    delay_days = _number(metrics.get("delay_days")) or 0
    planned = _number(metrics.get("planned_progress"))
    actual = _number(metrics.get("actual_progress"))
    progress_gap = (planned - actual) if planned is not None and actual is not None else 0
    cpi = _number(metrics.get("cpi"))
    spi = _number(metrics.get("spi"))
    document_score = _number(metrics.get("document_completeness_score")) or 0

    if delay_days > 0 or progress_gap > 5 or (spi is not None and spi < 0.9):
        severity = "Critical" if delay_days >= 30 or progress_gap >= 15 else "High" if delay_days >= 14 or progress_gap >= 8 else "Medium"
        risks.append(_risk(
            title="Schedule slippage",
            category="Schedule delay",
            severity=severity,
            probability=0.72 if severity in {"High", "Critical"} else 0.48,
            impact=f"{int(delay_days)} delay days and {round(progress_gap, 1)} percentage point progress gap.",
            explanation="Planned progress is ahead of the confirmed actual progress or forecast finish is beyond baseline.",
            action="Revise work sequence, update recovery schedule and track critical activities weekly.",
            evidence=[{"metric": "SPI", "value": spi}, {"metric": "delay_days", "value": delay_days}],
        ))

    if cpi is not None and cpi < 0.95:
        severity = "Critical" if cpi < 0.85 else "High" if cpi < 0.9 else "Medium"
        risks.append(_risk(
            title="Cost overrun risk",
            category="Cost overrun",
            severity=severity,
            probability=0.68,
            impact=f"CPI is {cpi}, below the target control range.",
            explanation="Earned value is behind actual cost or committed cost trend is above the baseline.",
            action="Review payment packages, freeze unsupported overruns and separate approved changes from uncontrolled variance.",
            evidence=[{"metric": "CPI", "value": cpi}, {"metric": "cost_variance", "value": metrics.get("cost_variance")}],
        ))

    workforce_gap = _workforce_gap(normalized)
    if workforce_gap > 0:
        risks.append(_risk(
            title="Low manpower on site",
            category="Low manpower",
            severity="High" if workforce_gap >= 15 else "Medium",
            probability=0.62,
            impact=f"{workforce_gap} workers below indicated requirement.",
            explanation="Current manpower is lower than the extracted recovery requirement.",
            action="Increase workforce on critical work fronts and validate daily productivity assumptions.",
            evidence=[{"metric": "workforce_gap", "value": workforce_gap}],
        ))

    material_sources = ((normalized.get("material_data") or [{}])[0] or {}).get("detected_material_sources") or 0
    if material_sources:
        risks.append(_risk(
            title="Material delivery delay",
            category="Material delivery delay",
            severity="Medium",
            probability=0.46,
            impact="Material records require delivery-date alignment with schedule stages.",
            explanation="Procurement or material sheets were detected and should be matched to critical path dates.",
            action="Confirm supplier dates, backup suppliers and long-lead material delivery windows.",
            evidence=[{"metric": "material_source_count", "value": material_sources}],
        ))

    if document_score < 70:
        risks.append(_risk(
            title="Missing document submission",
            category="Missing documents",
            severity="High" if document_score < 45 else "Medium",
            probability=0.54,
            impact=f"Document completeness score is {document_score}%.",
            explanation="Uploaded project records are incomplete for confident project performance review.",
            action="Upload missing schedule, cost, progress payment and decision register files.",
            evidence=[{"metric": "document_completeness_score", "value": document_score}],
        ))

    for warning in warnings[:4]:
        risks.append(_risk(
            title="Data quality risk",
            category="Data quality risk",
            severity="Medium",
            probability=0.42,
            impact="Some uploaded data could not be mapped with high confidence.",
            explanation=str(warning),
            action="Confirm unclear columns or upload a cleaner project control file.",
            evidence=[{"warning": str(warning)}],
            confidence=max(20, float(normalized.get("confidence_score") or 0)),
        ))

    if not risks:
        risks.append(_risk(
            title="Project performance review required",
            category="Data quality risk",
            severity="Low",
            probability=0.25,
            impact="No critical risk was generated from the available dashboard data.",
            explanation="Current uploaded files do not indicate a major schedule, cost or document control issue.",
            action="Continue weekly project control updates and upload fresh progress records.",
            evidence=[{"confidence_score": normalized.get("confidence_score")}],
        ))

    risks.sort(key=lambda item: SEVERITY_ORDER.get(item["severity"], 0), reverse=True)
    return risks


def _risk(
    *,
    title: str,
    category: str,
    severity: str,
    probability: float,
    impact: str,
    explanation: str,
    action: str,
    evidence: List[Dict[str, Any]],
    confidence: float | None = None,
) -> Dict[str, Any]:
    return {
        "risk_title": title,
        "title": title,
        "category": category,
        "severity": severity,
        "probability": round(probability, 2),
        "impact": impact,
        "explanation": explanation,
        "description": explanation,
        "recommended_action": action,
        "action": action,
        "responsible_party": "Project control team",
        "deadline": None,
        "status": "Open",
        "evidence": evidence,
        "confidence": round(confidence if confidence is not None else 70.0, 1),
    }


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _workforce_gap(normalized: Dict[str, Any]) -> int:
    current = None
    required = None
    for item in normalized.get("manpower_data") or []:
        if item.get("name") == "current_workforce":
            current = _number(item.get("value"))
        if item.get("name") == "required_workforce":
            required = _number(item.get("value"))
    if current is None or required is None:
        return 0
    return max(0, int(round(required - current)))

