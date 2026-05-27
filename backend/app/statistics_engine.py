from __future__ import annotations

from math import sqrt
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import ParsedProjectData


MIN_TREND_POINTS = 4
MIN_CORRELATION_POINTS = 4
MIN_EAC_PROGRESS_PCT = 5.0
MIN_FORECAST_PROGRESS_PCT = 10.0
LOW_STOCK_MEAN_THRESHOLD_PCT = 0.20


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(float(value), digits)


def _pct(value: Optional[float], digits: int = 2) -> Optional[float]:
    return _round(value, digits)


def _safe_values(values: Iterable[Any]) -> List[float]:
    return [n for n in (_num(v) for v in values) if n is not None]


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return a / b


def _currency(parsed: ParsedProjectData) -> str:
    return parsed.currency or "AZN"


def descriptive_stats(values: Iterable[Any]) -> Dict[str, Any]:
    """Small descriptive layer kept for diagnostics, but used only as support.

    The dashboard primarily exposes construction-control metrics below, not generic
    textbook statistics.
    """
    data = _safe_values(values)
    n = len(data)
    if not data:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "range": None, "variance": None, "std_dev": None, "cv_percent": None}
    avg = mean(data)
    var = sum((x - avg) ** 2 for x in data) / n if n else None
    std = sqrt(var) if var is not None else None
    cv = (std / abs(avg) * 100) if avg and std is not None else None
    return {
        "count": n,
        "min": _round(min(data)),
        "max": _round(max(data)),
        "mean": _round(avg),
        "median": _round(median(data)),
        "range": _round(max(data) - min(data)),
        "variance": _round(var),
        "std_dev": _round(std),
        "cv_percent": _round(cv),
    }


def _linear_regression(values: List[float]) -> Dict[str, Any]:
    """Trend guardrail for construction data.

    Two or three points can create a visually convincing but statistically weak
    line. We require at least four detected periods before showing slope, R² or
    a next-period forecast.
    """
    if len(values) < MIN_TREND_POINTS:
        return {
            "slope": None,
            "intercept": None,
            "r2": None,
            "direction": "Insufficient data",
            "forecast_next": None,
            "sample_size": len(values),
            "minimum_points_required": MIN_TREND_POINTS,
            "reliability_note": "At least 4 construction periods are required before trend/forecast is shown.",
        }
    xs = list(range(1, len(values) + 1))
    xbar = mean(xs)
    ybar = mean(values)
    den = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, values)) / den if den else 0.0
    intercept = ybar - slope * xbar
    predicted = [intercept + slope * x for x in xs]
    ss_tot = sum((y - ybar) ** 2 for y in values)
    ss_res = sum((y - yp) ** 2 for y, yp in zip(values, predicted))
    r2 = 1 - ss_res / ss_tot if ss_tot else None
    if abs(slope) < 0.01:
        direction = "Stable"
    elif slope > 0:
        direction = "Increasing"
    else:
        direction = "Decreasing"
    return {
        "slope": _round(slope),
        "intercept": _round(intercept),
        "r2": _round(max(0, min(1, r2)), 3) if r2 is not None else None,
        "direction": direction,
        "forecast_next": _round(intercept + slope * (len(values) + 1)),
        "sample_size": len(values),
        "minimum_points_required": MIN_TREND_POINTS,
        "reliability_note": "Trend is based on detected construction periods and should be checked against source documents.",
    }


def _pearson(x_values: List[float], y_values: List[float]) -> Optional[float]:
    n = min(len(x_values), len(y_values))
    if n < MIN_CORRELATION_POINTS:
        return None
    x = x_values[:n]
    y = y_values[:n]
    xbar = mean(x)
    ybar = mean(y)
    num = sum((a - xbar) * (b - ybar) for a, b in zip(x, y))
    den_x = sqrt(sum((a - xbar) ** 2 for a in x))
    den_y = sqrt(sum((b - ybar) ** 2 for b in y))
    if not den_x or not den_y:
        return None
    return _round(num / (den_x * den_y), 3)


def _correlation_label(value: Optional[float]) -> str:
    if value is None:
        return "Insufficient paired construction data"
    strength = abs(value)
    if strength >= 0.8:
        return "Strong positive construction relationship" if value > 0 else "Strong negative construction relationship"
    if strength >= 0.5:
        return "Moderate positive construction relationship" if value > 0 else "Moderate negative construction relationship"
    if strength >= 0.25:
        return "Weak positive construction relationship" if value > 0 else "Weak negative construction relationship"
    return "No clear construction relationship"


def _moving_average(values: List[float], window: int = 3) -> List[Optional[float]]:
    if not values:
        return []
    result: List[Optional[float]] = []
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        result.append(_round(mean(values[start : idx + 1])))
    return result


def _z_score_outliers(values: List[float], labels: Optional[List[str]] = None, threshold: float = 2.0) -> List[Dict[str, Any]]:
    if len(values) < 3:
        return []
    avg = mean(values)
    std = sqrt(sum((x - avg) ** 2 for x in values) / len(values))
    if not std:
        return []
    rows = []
    for idx, value in enumerate(values):
        z = (value - avg) / std
        if abs(z) >= threshold:
            rows.append({
                "label": labels[idx] if labels and idx < len(labels) else f"Item {idx + 1}",
                "value": _round(value),
                "z_score": _round(z),
                "method": "construction outlier check / z-score",
                "construction_note": "Review this work package, payment period or quantity because it deviates from the detected distribution.",
            })
    return rows[:8]


def _collect_cost_series(parsed: ParsedProjectData) -> Tuple[List[float], List[str]]:
    values: List[float] = []
    labels: List[str] = []
    evidence = parsed.evidence or {}
    f2_periods = evidence.get("f2_periods") or []
    if not f2_periods and isinstance(evidence.get("az_f2_parser"), dict):
        f2_periods = evidence.get("az_f2_parser", {}).get("periods") or []
    if isinstance(f2_periods, list):
        for idx, row in enumerate(f2_periods):
            if not isinstance(row, dict):
                continue
            value = _num(row.get("completed") or row.get("amount") or row.get("value") or row.get("cumulative"))
            if value is not None:
                values.append(value)
                labels.append(str(row.get("period") or row.get("date") or f"Progress Payment {idx + 1}"))
    section_breakdown = evidence.get("section_breakdown") or []
    if not values and isinstance(section_breakdown, list):
        for idx, row in enumerate(section_breakdown):
            if not isinstance(row, dict):
                continue
            value = _num(row.get("amount") or row.get("value") or row.get("total"))
            if value is not None:
                values.append(value)
                labels.append(str(row.get("section") or row.get("name") or f"Work package {idx + 1}"))
    if not values:
        f2_completed = _num(evidence.get("f2_completed_amount") or evidence.get("completed_amount"))
        if f2_completed is not None:
            values.append(f2_completed)
            labels.append("Progress Payment / completed amount")
    if not values:
        for label, value in [("Smeta baseline", parsed.planned_cost or parsed.total_cost), ("Progress Payment / actual", parsed.actual_cost)]:
            n = _num(value)
            if n is not None:
                values.append(n)
                labels.append(label)
    return values, labels


def _collect_progress_series(parsed: ParsedProjectData) -> Tuple[List[float], List[str]]:
    values: List[float] = []
    labels: List[str] = []
    evidence = parsed.evidence or {}
    for key in ["progress_periods", "actual_progress_periods", "schedule_periods", "monthly_progress"]:
        rows = evidence.get(key) or []
        if not isinstance(rows, list):
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            value = _num(row.get("actual") or row.get("progress") or row.get("actual_progress") or row.get("percent") or row.get("value"))
            if value is not None:
                values.append(value)
                labels.append(str(row.get("period") or row.get("date") or f"Progress period {idx + 1}"))
    if not values:
        values = _safe_values([parsed.planned_execution, parsed.actual_execution])
        labels = [label for label, value in [("Planned progress", parsed.planned_execution), ("Actual progress", parsed.actual_execution)] if _num(value) is not None]
    return values, labels


def _collect_workforce_series(parsed: ParsedProjectData) -> Tuple[List[float], List[str]]:
    values = _safe_values([parsed.workforce_required, parsed.workforce_current])
    labels = [label for label, value in [("Required workforce", parsed.workforce_required), ("Current workforce", parsed.workforce_current)] if _num(value) is not None]
    productivity = ((parsed.evidence or {}).get("workforce_productivity") or {}).get("activities") or []
    if isinstance(productivity, list):
        for idx, row in enumerate(productivity):
            if not isinstance(row, dict):
                continue
            for key in ["required_workers", "actual_workers", "workers"]:
                n = _num(row.get(key))
                if n is not None:
                    values.append(n)
                    labels.append(str(row.get("activity") or f"Activity {idx + 1}"))
                    break
    return values, labels


def _collect_material_series(parsed: ParsedProjectData) -> Tuple[List[float], List[str]]:
    values: List[float] = []
    labels: List[str] = []
    evidence = parsed.evidence or {}
    for key in ["material_stock", "materials", "procurement", "delivery_schedule"]:
        rows = evidence.get(key) or []
        if not isinstance(rows, list):
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            value = _num(row.get("stock") or row.get("quantity") or row.get("balance") or row.get("remaining") or row.get("amount"))
            if value is not None:
                values.append(value)
                labels.append(str(row.get("material") or row.get("item") or row.get("name") or f"Material {idx + 1}"))
    return values, labels


def _baseline_cost(parsed: ParsedProjectData) -> Optional[float]:
    return _num(parsed.planned_cost or parsed.total_cost)


def _actual_cost(parsed: ParsedProjectData) -> Optional[float]:
    return _num(parsed.actual_cost)


def _earned_value_metrics(parsed: ParsedProjectData) -> Dict[str, Any]:
    bac = _baseline_cost(parsed)  # Budget at completion / smeta baseline
    ac = _actual_cost(parsed)     # Actual cost / progress payment confirmed
    planned_pct = _num(parsed.planned_execution)
    actual_pct = _num(parsed.actual_execution)
    pv = (bac * planned_pct / 100) if bac is not None and planned_pct is not None else None
    ev = (bac * actual_pct / 100) if bac is not None and actual_pct is not None else None
    cv = (ev - ac) if ev is not None and ac is not None else None
    sv = (ev - pv) if ev is not None and pv is not None else None
    cpi = _safe_div(ev, ac)
    spi = _safe_div(ev, pv)
    eac = None
    eac_method = None
    eac_confidence = "Not enough construction progress evidence"
    eac_warning = None
    if actual_pct is not None and actual_pct < MIN_EAC_PROGRESS_PCT:
        eac_warning = f"EAC not calculated: progress is below {MIN_EAC_PROGRESS_PCT:g}% and forecast is unreliable."
        eac_confidence = "Too early to forecast"
    elif bac is not None and cpi not in (None, 0):
        eac = _safe_div(bac, cpi)
        eac_method = "BAC / CPI"
        eac_confidence = "Indicative EVM forecast"
    elif ac is not None and actual_pct not in (None, 0):
        eac = _safe_div(ac, actual_pct / 100)
        eac_method = "AC / actual progress"
        eac_confidence = "Fallback forecast — validate before commercial decisions"
    etc = (eac - ac) if eac is not None and ac is not None else None
    vac = (bac - eac) if bac is not None and eac is not None else None
    return {
        "budget_at_completion_bac": _round(bac),
        "planned_value_pv": _round(pv),
        "earned_value_ev": _round(ev),
        "actual_cost_ac": _round(ac),
        "cost_variance_cv": _round(cv),
        "schedule_variance_sv": _round(sv),
        "cost_performance_index_cpi": _round(cpi, 3),
        "schedule_performance_index_spi": _round(spi, 3),
        "estimate_at_completion_eac": _round(eac),
        "estimate_to_complete_etc": _round(etc),
        "variance_at_completion_vac": _round(vac),
        "eac_method": eac_method,
        "eac_confidence": eac_confidence,
        "eac_warning": eac_warning,
        "interpretation": _evm_interpretation(cpi, spi),
    }


def _evm_interpretation(cpi: Optional[float], spi: Optional[float]) -> str:
    notes = []
    if cpi is None:
        notes.append("CPI needs cost and progress evidence")
    elif cpi >= 1.0:
        notes.append("Cost efficiency is acceptable")
    else:
        notes.append("Cost efficiency is below baseline")
    if spi is None:
        notes.append("SPI needs planned and actual progress evidence")
    elif spi >= 1.0:
        notes.append("Schedule performance is on or above baseline")
    else:
        notes.append("Schedule performance is behind baseline")
    return "; ".join(notes)


def _commercial_control(parsed: ParsedProjectData) -> Dict[str, Any]:
    baseline = _baseline_cost(parsed)
    actual = _actual_cost(parsed)
    remaining = (baseline - actual) if baseline is not None and actual is not None else None
    utilization = (actual / baseline * 100) if baseline not in (None, 0) and actual is not None else None
    overbilling_flag = None
    actual_pct = _num(parsed.actual_execution)
    if utilization is not None and actual_pct is not None:
        overbilling_flag = utilization > actual_pct + 5
    return {
        "smeta_baseline": _round(baseline),
        "confirmed_progress_payment": _round(actual),
        "remaining_contract_value": _round(remaining),
        "progress_payment_utilization_percent": _round(utilization),
        "cost_variance_percent": _round(parsed.cost_variance_percent),
        "overbilling_watch": bool(overbilling_flag) if overbilling_flag is not None else None,
        "commercial_buffer_status": "Critical buffer" if remaining is not None and remaining < 0 else "Low buffer" if remaining is not None and baseline and remaining / baseline < 0.05 else "Buffer available" if remaining is not None else "Needs cost evidence",
    }


def _schedule_recovery(parsed: ParsedProjectData) -> Dict[str, Any]:
    planned = _num(parsed.planned_execution)
    actual = _num(parsed.actual_execution)
    gap = (planned - actual) if planned is not None and actual is not None else None
    delay = _num(parsed.delay_days)
    cur = _num(parsed.workforce_current)
    req = _num(parsed.workforce_required)
    workforce_gap = (req - cur) if req is not None and cur is not None else None
    recovery_pressure = None
    if gap is not None and gap > 0:
        recovery_pressure = min(100, gap * 4 + max(0, delay or 0) * 2 + max(0, workforce_gap or 0) * 1.5)
    elif delay is not None and delay > 0:
        recovery_pressure = min(100, delay * 3 + max(0, workforce_gap or 0) * 1.5)
    return {
        "planned_progress_percent": _round(planned),
        "actual_progress_percent": _round(actual),
        "progress_gap_percent": _round(gap),
        "delay_days": _round(delay),
        "current_workforce": _round(cur),
        "required_workforce": _round(req),
        "additional_workers_required": _round(workforce_gap if workforce_gap and workforce_gap > 0 else 0),
        "recovery_pressure_score": _round(recovery_pressure),
        "recovery_status": "Recovery action needed" if recovery_pressure and recovery_pressure >= 40 else "Monitor" if recovery_pressure is not None else "Needs schedule/workforce evidence",
    }


def _material_continuity(parsed: ParsedProjectData) -> Dict[str, Any]:
    material_values, material_labels = _collect_material_series(parsed)
    stats = descriptive_stats(material_values)
    low_stock_threshold = None
    if material_values:
        mean_value = _num(stats.get("mean"))
        low_stock_threshold = (mean_value * LOW_STOCK_MEAN_THRESHOLD_PCT) if mean_value is not None else None
        low_stock = [label for label, value in zip(material_labels, material_values) if low_stock_threshold is not None and value < low_stock_threshold]
    else:
        low_stock = []
    return {
        "material_items_detected": len(material_values),
        "material_stock_statistics": stats,
        "low_stock_candidates": low_stock[:5],
        "low_stock_threshold": _round(low_stock_threshold),
        "low_stock_method": "value < 20% of detected mean stock" if material_values else "needs material stock, consumption and delivery data",
        "stockout_readiness": "Material stock data detected — confirm against consumption rate and lead time" if material_values else "Needs material stock, consumption and delivery data",
    }


def _risk_weighted_control(risk: Dict[str, Any]) -> Dict[str, Any]:
    components = (risk or {}).get("components", {}) if isinstance(risk, dict) else {}
    if not isinstance(components, dict):
        components = {}
    weights = {
        "schedule": 0.30,
        "cost": 0.25,
        "labor": 0.15,
        "procurement": 0.15,
        "quality": 0.10,
        "documentation": 0.05,
    }
    weighted_rows = []
    total = 0.0
    used = 0.0
    for name, weight in weights.items():
        value = _num(components.get(name))
        if value is None:
            continue
        contribution = value * weight
        total += contribution
        used += weight
        weighted_rows.append({"risk_component": name.title(), "score": _round(value), "weight": weight, "weighted_contribution": _round(contribution)})
    normalized = total / used if used else _num((risk or {}).get("score"))
    return {
        "weighted_risk_score": _round(normalized),
        "rows": weighted_rows,
        "decision_level": "High attention" if normalized and normalized >= 65 else "Management watch" if normalized and normalized >= 40 else "Controlled" if normalized is not None else "Needs risk evidence",
    }


def _forecast(parsed: ParsedProjectData, trend: Dict[str, Any]) -> Dict[str, Any]:
    baseline = _baseline_cost(parsed)
    actual = _actual_cost(parsed)
    progress = _num(parsed.actual_execution)
    final_cost = None
    method = None
    confidence = "Not enough construction data"
    note = "Forecast requires sufficient progress or at least 4 reliable cost periods."
    if progress is not None and progress < MIN_FORECAST_PROGRESS_PCT:
        confidence = f"Very early stage — forecast not reliable below {MIN_FORECAST_PROGRESS_PCT:g}% progress"
        note = "Final cost forecast is suppressed to avoid misleading early-stage extrapolation."
    elif actual is not None and progress and progress >= MIN_FORECAST_PROGRESS_PCT:
        final_cost = actual / (progress / 100)
        method = "actual cost / actual progress"
        confidence = "Indicative construction forecast"
        note = "Forecast uses detected actual/progress payment and actual progress. Confirm before commercial decisions."
    elif trend.get("forecast_next") is not None and (trend.get("sample_size") or 0) >= MIN_TREND_POINTS:
        final_cost = trend.get("forecast_next")
        method = "detected cost trend"
        confidence = "Trend-based indicative forecast"
        note = "Forecast uses at least 4 detected cost/payment periods."
    overrun = (final_cost - baseline) if final_cost is not None and baseline is not None else None
    return {
        "estimated_final_cost": _round(final_cost),
        "estimated_overrun_amount": _round(overrun),
        "estimated_overrun_percent": _round((overrun / baseline * 100) if overrun is not None and baseline else None),
        "method": method,
        "confidence": confidence,
        "minimum_progress_required_percent": MIN_FORECAST_PROGRESS_PCT,
        "minimum_trend_points_required": MIN_TREND_POINTS,
        "note": note,
    }


def _density(parsed: ParsedProjectData) -> int:
    signals = 0
    possible = 11
    for value in [parsed.planned_execution, parsed.actual_execution, parsed.delay_days, parsed.total_cost, parsed.planned_cost, parsed.actual_cost, parsed.workforce_current, parsed.workforce_required, parsed.baseline_finish, parsed.estimated_finish]:
        if value not in (None, ""):
            signals += 1
    if parsed.sheets:
        signals += 1
    return int(round(signals / possible * 100))


def _construction_readiness(parsed: ParsedProjectData, values: List[float]) -> str:
    signals = _density(parsed)
    if signals >= 75 and len(values) >= 4:
        return "Construction-ready"
    if signals >= 50 and len(values) >= 2:
        return "Review-ready"
    if signals >= 25:
        return "Limited construction evidence"
    return "Insufficient construction evidence"


def build_statistical_analytics(parsed: ParsedProjectData, risk: Dict[str, Any], mode: str = "all") -> Dict[str, Any]:
    """Return construction-specific statistical analytics for DevBareun.

    This layer intentionally avoids showing generic statistics as the product goal.
    It converts statistics into construction controls: EVM, cost/payment exposure,
    schedule recovery, workforce gap, material continuity, risk weighting, outliers
    and construction forecasts.
    """
    mode = (mode or "all").lower()
    cost_values, cost_labels = _collect_cost_series(parsed)
    progress_values, progress_labels = _collect_progress_series(parsed)
    workforce_values, workforce_labels = _collect_workforce_series(parsed)
    material_values, material_labels = _collect_material_series(parsed)
    risk_values = _safe_values((risk or {}).get("components", {}).values() if isinstance((risk or {}).get("components"), dict) else [])

    if mode == "cost":
        primary_series, primary_labels = cost_values, cost_labels
    elif mode in {"schedule", "workforce"}:
        primary_series, primary_labels = progress_values + workforce_values, progress_labels + workforce_labels
    elif mode == "material":
        primary_series, primary_labels = material_values, material_labels
    elif mode == "risk":
        primary_series, primary_labels = risk_values, ["Schedule", "Cost", "Labor", "Procurement", "Quality"][: len(risk_values)]
    else:
        primary_series = cost_values + progress_values + workforce_values + material_values + risk_values
        primary_labels = cost_labels + progress_labels + workforce_labels + material_labels + ["Risk component"] * len(risk_values)

    trend_input = cost_values if len(cost_values) >= 2 else progress_values if len(progress_values) >= 2 else workforce_values if len(workforce_values) >= 2 else primary_series
    trend = _linear_regression(trend_input)

    correlations = []
    pairs = [
        ("Progress earned value vs actual cost", progress_values, cost_values),
        ("Workforce level vs progress", workforce_values, progress_values),
        ("Workforce level vs cost/payment", workforce_values, cost_values),
        ("Material stock vs progress", material_values, progress_values),
    ]
    for name, x, y in pairs:
        sample_size = min(len(x), len(y))
        corr = _pearson(x, y)
        correlations.append({
            "pair": name,
            "pearson_r": corr,
            "sample_size": sample_size,
            "minimum_points_required": MIN_CORRELATION_POINTS,
            "interpretation": _correlation_label(corr) if corr is not None else "Insufficient data for correlation",
        })

    outliers = _z_score_outliers(primary_series, primary_labels)
    evm = _earned_value_metrics(parsed)
    commercial = _commercial_control(parsed)
    schedule = _schedule_recovery(parsed)
    material = _material_continuity(parsed)
    risk_weighted = _risk_weighted_control(risk)

    variance_rows = []
    if commercial["smeta_baseline"] is not None or commercial["confirmed_progress_payment"] is not None:
        variance_rows.append({
            "metric": "Smeta vs Progress Payment variance",
            "baseline": commercial["smeta_baseline"],
            "actual": commercial["confirmed_progress_payment"],
            "variance": _round((commercial["confirmed_progress_payment"] or 0) - (commercial["smeta_baseline"] or 0)) if commercial["smeta_baseline"] is not None and commercial["confirmed_progress_payment"] is not None else None,
            "variance_percent": commercial["cost_variance_percent"],
        })
    if schedule["planned_progress_percent"] is not None or schedule["actual_progress_percent"] is not None:
        variance_rows.append({
            "metric": "Plan vs Actual progress variance",
            "baseline": schedule["planned_progress_percent"],
            "actual": schedule["actual_progress_percent"],
            "variance": _round((schedule["actual_progress_percent"] or 0) - (schedule["planned_progress_percent"] or 0)) if schedule["planned_progress_percent"] is not None and schedule["actual_progress_percent"] is not None else None,
            "variance_percent": _round((schedule["actual_progress_percent"] or 0) - (schedule["planned_progress_percent"] or 0)) if schedule["planned_progress_percent"] is not None and schedule["actual_progress_percent"] is not None else None,
        })
    if schedule["required_workforce"] is not None or schedule["current_workforce"] is not None:
        variance_rows.append({
            "metric": "Required vs Current workforce variance",
            "baseline": schedule["required_workforce"],
            "actual": schedule["current_workforce"],
            "variance": _round((schedule["current_workforce"] or 0) - (schedule["required_workforce"] or 0)) if schedule["required_workforce"] is not None and schedule["current_workforce"] is not None else None,
            "variance_percent": _round(((schedule["current_workforce"] or 0) - (schedule["required_workforce"] or 0)) / schedule["required_workforce"] * 100) if schedule["required_workforce"] else None,
        })

    return {
        "summary": {
            "mode": mode,
            "sample_size": len(primary_series),
            "data_density": _density(parsed),
            "statistical_readiness": _construction_readiness(parsed, primary_series),
            "purpose": "Construction control statistics",
        },
        "construction_statistics": {
            "earned_value_management": evm,
            "commercial_payment_control": commercial,
            "schedule_recovery_statistics": schedule,
            "material_continuity_statistics": material,
            "risk_weighted_control": risk_weighted,
        },
        "descriptive_statistics": {
            "cost": descriptive_stats(cost_values),
            "progress": descriptive_stats(progress_values),
            "workforce": descriptive_stats(workforce_values),
            "material": descriptive_stats(material_values),
            "risk_components": descriptive_stats(risk_values),
            "selected_package": descriptive_stats(primary_series),
        },
        "variance_analysis": variance_rows,
        "trend_analysis": {
            **trend,
            "moving_average_3": _moving_average(trend_input, 3),
            "method": "construction trend over detected progress, payment, workforce or material series",
        },
        "correlation_analysis": correlations,
        "outlier_detection": {
            "method": "construction control outlier check / z-score threshold ±2.0",
            "outliers": outliers,
            "status": "No construction outliers detected" if not outliers else "Construction outliers require review",
        },
        "forecasting": _forecast(parsed, trend),
        "functions_available": [
            "Earned Value Management: PV, EV, AC, CV, SV, CPI, SPI",
            "Estimate at Completion: EAC, ETC, VAC",
            "Smeta vs Progress Payment variance",
            "Progress payment utilization and commercial buffer",
            "Plan vs actual progress variance",
            "Delay and recovery pressure scoring",
            "Required vs current workforce gap",
            "Material stock continuity statistics",
            "Construction trend and moving average",
            "Construction correlation checks",
            "Work package / payment outlier detection",
            "Risk-weighted construction score",
            "Final cost forecast and overrun estimate with early-stage guardrails",
        ],
    }
