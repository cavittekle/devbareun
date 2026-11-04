"""Executive execution report (icra hesabatı) for the director.

Method (DevBareun icra hesabatı, v2):

* **Fact %** = cumulative F-2 value / estimate value, both before VAT and
  without the contingency reserve. F-2 is accepted work value, not a physical
  measurement; the report says so.
* **Plan %** = every estimate section's value is spread evenly over the
  baseline duration of the schedule activities of the same work type in the
  same building and summed to the report date (a value-weighted S-curve).
* **Delay (days)** = report date − the date the plan reached today's fact %
  (earned schedule).
* **Forecast** = report date + (baseline finish − that date): the earliest
  finish if the schedule's own pace is restored. The last three months' pace
  is shown only when it gives a realistic date.

Without estimate lines the same layout is built from the schedule's activity
weights and progress (``method = activity_weights``).
"""
from __future__ import annotations

import calendar
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import categories as cat
from .model import Activity, ContractTerms, CostLine, DelayInput, F3Summary, PaymentCertificate

SCHEMA = "devbareun.execution-report/v2"
RECENT_PACE_MONTHS = 3
UNREALISTIC_MONTHS = 36
DEFAULT_VAT_PCT = 18.0
DAYS_PER_MONTH = 30.44
OTHER = "other"

MONTHS_AZ = ("Yan", "Fev", "Mar", "Apr", "May", "İyn", "İyl", "Avq", "Sen", "Okt", "Noy", "Dek")
MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS_AZ_FULL = ("Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr")
MONTHS_EN_FULL = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


# ----------------------------------------------------------------- format
def num(value: Optional[float], digits: int = 1, lang: str = "az") -> str:
    if value is None:
        return "—"
    text = f"{value:,.{digits}f}".replace(",", " ")
    return text.replace(".", ",") if lang == "az" else text


def mln(value: Optional[float], lang: str = "az", digits: int = 2) -> str:
    return "—" if value is None else num(value / 1_000_000, digits, lang)


def pct(value: Optional[float], lang: str = "az", digits: int = 1) -> str:
    return "—" if value is None else f"{num(value, digits, lang)}%"


def dmy(value: Optional[date]) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"


def month_year(value: Optional[date], lang: str = "az") -> str:
    if not value:
        return "—"
    names = MONTHS_AZ_FULL if lang == "az" else MONTHS_EN_FULL
    return f"{names[value.month - 1]} {value.year}"


def _t(az: str, en: str) -> Dict[str, str]:
    return {"az": az, "en": en}


def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _month_ends(start: date, finish: date) -> List[date]:
    out, current = [], _month_end(start)
    while current <= _month_end(finish):
        out.append(current)
        nxt = current + timedelta(days=1)
        current = _month_end(nxt)
    return out


def _add_months(value: date, months: float) -> date:
    return value + timedelta(days=round(months * DAYS_PER_MONTH))


def _r(value: Optional[float], digits: int = 1) -> Optional[float]:
    return None if value is None else round(value, digits)


# ----------------------------------------------------------------- buckets
@dataclass
class _Bucket:
    building: Optional[str]
    category: str
    value: float = 0.0
    cum: float = 0.0
    period: float = 0.0
    start: Optional[date] = None
    finish: Optional[date] = None
    window_note: Optional[str] = None
    lines: List[CostLine] = field(default_factory=list)

    def plan_fraction(self, on: date) -> float:
        if not self.start or not self.finish:
            return 0.0
        if on < self.start:
            return 0.0
        if on >= self.finish:
            return 1.0
        total = (self.finish - self.start).days + 1
        return ((on - self.start).days + 1) / total

    @property
    def fact_pct(self) -> float:
        return self.cum / self.value * 100 if self.value > 0 else 0.0


def _activity_keys(act: Activity) -> Tuple[Optional[str], Optional[str]]:
    return cat.building_of(act.wbs, act.name), cat.categorize(act.wbs, act.name)


def _windows(activities: Sequence[Activity]) -> Dict[Tuple[Optional[str], Optional[str]], Tuple[date, date]]:
    out: Dict[Tuple[Optional[str], Optional[str]], Tuple[date, date]] = {}
    for act in activities:
        if not act.planned_start or not act.planned_finish:
            continue
        key = _activity_keys(act)
        start, finish = act.planned_start, max(act.planned_finish, act.planned_start)
        if key in out:
            s, f = out[key]
            out[key] = (min(s, start), max(f, finish))
        else:
            out[key] = (start, finish)
    return out


def _union(windows: Iterable[Tuple[date, date]]) -> Optional[Tuple[date, date]]:
    items = list(windows)
    if not items:
        return None
    return min(s for s, _ in items), max(f for _, f in items)


def _assign_windows(buckets: List[_Bucket], activities: Sequence[Activity], quality: List[Dict[str, Any]]) -> None:
    windows = _windows(activities)
    project = _union(windows.values())
    by_category: Dict[Optional[str], List[Tuple[date, date]]] = defaultdict(list)
    by_building: Dict[Optional[str], List[Tuple[date, date]]] = defaultdict(list)
    for (building, category), window in windows.items():
        by_category[category].append(window)
        by_building[building].append(window)
    missing: Dict[str, List[str]] = defaultdict(list)
    for bucket in buckets:
        key = (bucket.building, bucket.category)
        window = windows.get(key)
        if window is None and bucket.category != OTHER:
            window = windows.get((None, bucket.category))
            if window is None and by_category.get(bucket.category):
                window = _union(by_category[bucket.category])
                if bucket.building and by_building.get(bucket.building):
                    missing[bucket.building].append(bucket.category)
        if window is None and bucket.building and by_building.get(bucket.building):
            window = _union(by_building[bucket.building])
        if window is None:
            window = project
        if window:
            bucket.start, bucket.finish = window
    for building, cats in sorted(missing.items(), key=lambda kv: cat.building_sort_key(kv[0])):
        names_az = ", ".join(cat.label(c, "az").lower() for c in cats)
        names_en = ", ".join(cat.label(c, "en").lower() for c in cats)
        quality.append({"code": "schedule_missing_activities", "severity": "warning", "building": building, "categories": cats,
                        "az": f"Qrafikdə {building} üçün {names_az} fəaliyyətləri yoxdur; bütün binalar üzrə həmin işlərin müddəti götürüldü.",
                        "en": f"The schedule has no {names_en} activities for {building}; the combined duration of these works in all buildings was used."})
    # Sequence check: a work type planned to start before the one it depends on.
    by_key = {(b.building, b.category): b for b in buckets}
    for bucket in buckets:
        before = cat.DEPENDS_ON.get(bucket.category)
        if not before:
            continue
        pred = by_key.get((bucket.building, before))
        if pred and pred.start and bucket.start and pred.finish and bucket.finish and bucket.finish < pred.start:
            bucket.window_note = "illogical"
            quality.append({"code": "schedule_illogical_sequence", "severity": "warning", "building": bucket.building,
                            "az": f"{bucket.building or 'Layihə'}: qrafikdə {cat.label(bucket.category, 'az').lower()} {cat.label(before, 'az').lower()} başlamazdan əvvəl bitir; {cat.label(before, 'az').lower()} müddəti götürüldü.",
                            "en": f"{bucket.building or 'Project'}: the schedule finishes {cat.label(bucket.category, 'en').lower()} before {cat.label(before, 'en').lower()} starts; the {cat.label(before, 'en').lower()} duration was used."})
            bucket.start, bucket.finish = pred.start, pred.finish


def _buckets_from_costs(lines: Sequence[CostLine]) -> List[_Bucket]:
    buckets: Dict[Tuple[Optional[str], str], _Bucket] = {}
    for line in lines:
        category = line.category or OTHER
        building = line.building
        if category == cat.SITE:
            building = None  # site works belong to the whole estate
        key = (building, category)
        bucket = buckets.setdefault(key, _Bucket(building=building, category=category))
        bucket.value += line.estimate_value or 0.0
        bucket.cum += line.cum_value or 0.0
        bucket.period += line.period_value or 0.0
        bucket.lines.append(line)
    return [b for b in buckets.values() if b.value > 0 or b.cum > 0]


def _buckets_from_activities(activities: Sequence[Activity]) -> List[_Bucket]:
    out: List[_Bucket] = []
    for act in activities:
        if not act.planned_start or not act.planned_finish:
            continue
        building, category = _activity_keys(act)
        weight = act.weight if act.weight and act.weight > 0 else float((act.planned_finish - act.planned_start).days + 1)
        progress = max(0.0, min(100.0, act.progress or (100.0 if act.actual_finish else 0.0)))
        out.append(_Bucket(building=building if category != cat.SITE else None, category=category or OTHER, value=weight,
                           cum=weight * progress / 100, start=act.planned_start, finish=max(act.planned_finish, act.planned_start)))
    return out


# ---------------------------------------------------------------- inputs
def _contract(inp: DelayInput) -> ContractTerms:
    terms = ContractTerms(**vars(inp.contract))
    info = inp.project
    terms.update(ContractTerms(client=info.client, contractor=info.contractor, value_with_vat=info.contract_value,
                               start=info.contract_start, finish=info.contract_finish, subject=None))
    if terms.finish is None and terms.start and terms.duration_months:
        terms.finish = _add_months(terms.start, terms.duration_months)
    if terms.duration_months is None and terms.start and terms.finish:
        terms.duration_months = round((terms.finish - terms.start).days / DAYS_PER_MONTH)
    return terms


def _monthly_f2(payments: Sequence[PaymentCertificate]) -> Dict[date, float]:
    by_month: Dict[date, float] = defaultdict(float)
    for cert in payments:
        if cert.period and cert.amount is not None:
            by_month[_month_end(cert.period)] += cert.amount
    return dict(by_month)


def _latest_f3(items: Sequence[F3Summary]) -> Optional[F3Summary]:
    dated = [f for f in items if f.period]
    if dated:
        return max(dated, key=lambda f: f.period)
    return items[-1] if items else None


# ------------------------------------------------------------------ main
def build_executive(inp: DelayInput, report_date: date,
                    monthly: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Executive report data. ``monthly`` is the engine's monthly series; it
    gives the fact curve when there is no estimate (activity weights mode)."""
    quality: List[Dict[str, Any]] = []
    terms = _contract(inp)
    lines = [line for line in inp.cost_lines if (line.estimate_value or 0) > 0 or (line.cum_value or 0) > 0]
    method = "estimate_value" if lines else "activity_weights"
    buckets = _buckets_from_costs(lines) if lines else _buckets_from_activities(inp.activities)
    if not buckets:
        return {"schema": SCHEMA, "ok": False}
    if lines:
        _assign_windows(buckets, inp.activities, quality)
        unclassified = sum(b.value for b in buckets if b.category == OTHER)
        total_value = sum(b.value for b in buckets)
        if unclassified > 0.02 * total_value:
            quality.append({"code": "estimate_unclassified", "severity": "info",
                            "az": f"Smeta dəyərinin {pct(unclassified / total_value * 100, 'az')}-i iş növünə aid edilmədi (bölmə adı tanınmadı).",
                            "en": f"{pct(unclassified / total_value * 100, 'en')} of the estimate value could not be given a work type (unknown section name)."})
    if not any(b.start for b in buckets):
        return {"schema": SCHEMA, "ok": False}

    starts = [b.start for b in buckets if b.start]
    finishes = [b.finish for b in buckets if b.finish]
    project_start = min(starts)
    baseline_finish = max(finishes)
    total = sum(b.value for b in buckets)
    cum_total = sum(b.cum for b in buckets)

    def plan_pct(on: date) -> float:
        return sum(b.value * b.plan_fraction(on) for b in buckets) / total * 100 if total else 0.0

    # Fact from the latest cumulative F-2 total when lines have no cumulative.
    monthly_f2 = _monthly_f2(inp.payments)
    if lines and cum_total == 0:
        cumulative = [c for c in inp.payments if c.cumulative]
        if cumulative:
            cum_total = max(cumulative, key=lambda c: c.period or date.min).cumulative or 0.0
            quality.append({"code": "fact_from_f2_cumulative", "severity": "info",
                            "az": "Smeta sətirlərində kumulyativ dəyər yoxdur; fakt son F-2 aktının kumulyativ məbləğindən götürüldü.",
                            "en": "Estimate lines have no cumulative value; fact uses the latest F-2 cumulative total."})
    fact = cum_total / total * 100 if total else 0.0
    plan = plan_pct(report_date)

    # Earned schedule: the date the plan reached today's fact.
    es_date = project_start
    if fact >= 100:
        es_date = report_date
    else:
        day = project_start
        while day <= baseline_finish and plan_pct(day) < fact:
            day += timedelta(days=1)
        es_date = min(day, baseline_finish)
    delay_days = max(0, (report_date - es_date).days) if fact < 100 else 0
    gap = fact - plan

    # Monthly series (value before VAT).
    horizon_end = max(baseline_finish, terms.finish or baseline_finish, report_date)
    months = _month_ends(project_start, horizon_end)
    previous = 0.0
    series = []
    actual_running = 0.0
    f2_months = {m: v for m, v in monthly_f2.items() if m <= _month_end(report_date)}
    known_sum = sum(f2_months.values())
    offset = cum_total - known_sum if method == "estimate_value" and f2_months and cum_total > known_sum + 1 else 0.0
    first_actual = min(f2_months) if f2_months else None
    weights = method == "activity_weights"
    weights_fact: Dict[date, float] = {}
    if weights:
        for row in monthly or []:
            try:
                key = date.fromisoformat(str(row.get("month_end")))
            except ValueError:
                continue
            if row.get("actual_cumulative_pct") is not None and key <= _month_end(report_date):
                weights_fact[key] = float(row["actual_cumulative_pct"])
    for month in months:
        p = plan_pct(month)
        point = {"month": month.isoformat(), "plan_pct": _r(p, 2),
                 "plan_value": None if weights else _r((p - previous) / 100 * total, 2)}
        previous = p
        if weights:
            # Weights are not money: F-2 amounts are shown as bars only.
            if month <= _month_end(report_date):
                amount = f2_months.get(month)
                point["f2_value"] = _r(amount, 2) if amount is not None else None
            if month in weights_fact:
                point["fact_pct"] = _r(weights_fact[month], 2)
        elif month <= _month_end(report_date):
            amount = f2_months.get(month)
            point["f2_value"] = _r(amount, 2) if amount is not None else (0.0 if f2_months and first_actual and month >= first_actual else None)
            if f2_months:
                actual_running += amount or 0.0
                if first_actual and month == first_actual:
                    actual_running += offset
                if first_actual and month >= first_actual:
                    point["fact_pct"] = _r(actual_running / total * 100, 2) if total else None
        series.append(point)
    if series and (weights and not weights_fact or not weights and not f2_months):
        # No monthly F-2: only today's fact point is known.
        for point in series:
            if point["month"] == _month_end(report_date).isoformat():
                point["fact_pct"] = _r(fact, 2)
    if offset:
        quality.append({"code": "f2_early_months_missing", "severity": "info",
                        "az": f"Aylıq F-2 aktlarının cəmi kumulyativ dəyərdən {mln(offset, 'az')} mln az; fərq ilk akt ayına əlavə edildi.",
                        "en": f"Monthly F-2 certificates add up to {mln(offset, 'en')} m less than the cumulative value; the difference is put in the first month."})
    missing_f2 = [m for m in months if first_actual and first_actual <= m <= _month_end(report_date) and m not in f2_months]

    # Pace and forecast.
    remaining = max(0.0, total - cum_total)
    recent_months = [m for m in months if m <= _month_end(report_date)][-RECENT_PACE_MONTHS:]
    recent_pace = (sum(f2_months.get(m, 0.0) for m in recent_months) / len(recent_months)) if f2_months and recent_months else None
    if weights:
        # Pace in weight units from the fact curve (last months' gain).
        recent_pace = None
        known = sorted(weights_fact)
        if len(known) >= 2:
            last = known[-1]
            base = [m for m in known if m < last][-RECENT_PACE_MONTHS:]
            if base:
                span = len([m for m in known if base[0] < m <= last]) or 1
                recent_pace = max(0.0, (weights_fact[last] - weights_fact[base[0]]) / 100 * total / span)
    plan_remaining_days = max(0, (baseline_finish - es_date).days)
    earliest = report_date + timedelta(days=plan_remaining_days) if fact < 100 else report_date
    schedule_pace = remaining / max(plan_remaining_days / DAYS_PER_MONTH, 1.0) if remaining else 0.0
    contract_finish = terms.finish
    months_left = (contract_finish - report_date).days / DAYS_PER_MONTH if contract_finish else None
    required_pace = remaining / months_left if months_left and months_left > 0.25 else None
    current_months = remaining / recent_pace if recent_pace and recent_pace > 0 else None
    current_finish = _add_months(report_date, current_months) if current_months is not None and current_months <= UNREALISTIC_MONTHS else None
    delay_vs_contract = (earliest - contract_finish).days if contract_finish else None
    forecast = {
        "earliest_finish": earliest.isoformat(),
        "basis": "schedule_pace",
        "plan_remaining_days": plan_remaining_days,
        "schedule_pace": _r(schedule_pace, 2),
        "recent_pace": _r(recent_pace, 2),
        "recent_pace_months": len(recent_months),
        "required_pace": _r(required_pace, 2),
        "required_vs_recent": _r(required_pace / recent_pace, 1) if required_pace and recent_pace else None,
        "schedule_vs_recent": _r(schedule_pace / recent_pace, 1) if schedule_pace and recent_pace else None,
        "current_pace_months": _r(current_months, 1),
        "current_pace_finish": current_finish.isoformat() if current_finish else None,
        "current_pace_unacceptable": bool(current_months is not None and current_months > UNREALISTIC_MONTHS) or (recent_pace == 0 and remaining > 0),
        "delay_vs_contract_days": delay_vs_contract,
        "contract_feasible": bool(contract_finish and earliest <= contract_finish),
        "remaining_value": _r(remaining, 2),
        "remaining_pct": _r(remaining / total * 100, 1) if total else None,
        "pace_unit": "pct" if weights else "money",
    }
    if weights:
        # Weights have no money meaning: express paces as % of the works per month.
        for key in ("schedule_pace", "recent_pace", "required_pace"):
            if forecast[key] is not None and total:
                forecast[key] = _r(forecast[key] / total * 100, 2)
        forecast["remaining_value"] = None

    # Penalty (28.1).
    penalty = None
    if terms.penalty_pct_per_day:
        cap = terms.penalty_cap_pct
        cap_days = math.ceil(cap / terms.penalty_pct_per_day) if cap else None
        penalty = {
            "pct_per_day": terms.penalty_pct_per_day,
            "cap_pct": cap,
            "cap_amount": _r(terms.value_with_vat * cap / 100, 2) if cap and terms.value_with_vat else None,
            "cap_days": cap_days,
            "cap_date": (contract_finish + timedelta(days=cap_days)).isoformat() if cap_days and contract_finish else None,
            "at_forecast_pct": _r(min(cap or 100.0, max(0, delay_vs_contract or 0) * terms.penalty_pct_per_day), 2),
        }

    money_cum = cum_total
    if weights:
        paid = [c for c in inp.payments if c.cumulative]
        money_cum = (max(paid, key=lambda c: c.period or date.min).cumulative if paid
                     else sum(c.amount or 0 for c in inp.payments)) or 0.0
    finance = _finance(inp, terms, money_cum, quality)
    physical = _physical(lines)
    category_rows = _category_rows(buckets, report_date, total)
    building_rows = _building_rows(buckets, report_date)
    result = {
        "schema": SCHEMA,
        "ok": True,
        "method": method,
        "report_date": report_date.isoformat(),
        "project_start": project_start.isoformat(),
        "baseline_finish": baseline_finish.isoformat(),
        "contract": _contract_dict(terms),
        "totals": {
            "estimate_value": _r(total, 2),
            "cum_value": _r(cum_total, 2),
            "period_value": _r(sum(b.period for b in buckets), 2),
            "plan_pct": _r(plan, 1),
            "fact_pct": _r(fact, 1),
            "gap_pp": _r(gap, 1),
            "delay_days": delay_days,
            "delay_months": _r(delay_days / DAYS_PER_MONTH, 1),
            "earned_schedule_date": es_date.isoformat(),
            "status": _status(gap),
        },
        "monthly": series,
        "f2_missing_months": [m.isoformat() for m in missing_f2],
        "forecast": forecast,
        "penalty": penalty,
        "finance": finance,
        "physical": physical,
        "categories": category_rows,
        "buildings": building_rows,
        "data_quality": quality,
    }
    result["texts"] = _texts(result)
    return result


def _status(gap: float) -> str:
    if gap >= -5:
        return "on_track"
    if gap >= -15:
        return "minor"
    if gap >= -50:
        return "serious"
    return "critical"


STATUS_LABELS = {
    "on_track": _t("Qrafik üzrə", "On track"),
    "minor": _t("Gecikmə", "Behind"),
    "serious": _t("Ciddi gerilik", "Seriously behind"),
    "critical": _t("Kritik", "Critical"),
}


def _contract_dict(terms: ContractTerms) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in vars(terms).items():
        out[key] = value.isoformat() if isinstance(value, date) else value
    return out


def _category_rows(buckets: Sequence[_Bucket], on: date, total: float) -> List[Dict[str, Any]]:
    groups: Dict[str, List[_Bucket]] = defaultdict(list)
    for bucket in buckets:
        groups[bucket.category].append(bucket)
    rows = []
    for category in list(cat.CATEGORIES) + [OTHER]:
        items = groups.get(category)
        if not items:
            continue
        value = sum(b.value for b in items)
        if value <= 0:
            continue
        plan = sum(b.value * b.plan_fraction(on) for b in items) / value * 100
        fact = sum(b.cum for b in items) / value * 100
        rows.append({"category": category, "value": _r(value, 2), "share_pct": _r(value / total * 100, 1) if total else None,
                     "plan_pct": _r(plan, 1), "fact_pct": _r(fact, 1), "gap_pp": _r(fact - plan, 1), "status": _status(fact - plan),
                     "remaining_value": _r(value - sum(b.cum for b in items), 2)})
    return rows


def _building_rows(buckets: Sequence[_Bucket], on: date) -> List[Dict[str, Any]]:
    groups: Dict[Optional[str], List[_Bucket]] = defaultdict(list)
    for bucket in buckets:
        groups[bucket.building].append(bucket)
    rows = []
    for building in sorted((b for b in groups if b), key=cat.building_sort_key):
        items = groups[building]
        value = sum(b.value for b in items)
        if value <= 0:
            continue
        plan = sum(b.value * b.plan_fraction(on) for b in items) / value * 100
        fact = sum(b.cum for b in items) / value * 100
        by_cat = {}
        for category in (cat.FRAME, cat.MASONRY, cat.ENVELOPE, cat.FINISHING, cat.MEP):
            sub = [b for b in items if b.category == category]
            sub_value = sum(b.value for b in sub)
            by_cat[category] = _r(sum(b.cum for b in sub) / sub_value * 100, 0) if sub_value > 0 else None
        finishes = [b.finish for b in items if b.finish]
        rows.append({"building": building, "plan_finish": max(finishes).isoformat() if finishes else None,
                     "plan_pct": _r(plan, 1), "fact_pct": _r(fact, 1), "gap_pp": _r(fact - plan, 1),
                     "categories": by_cat, "period_value": _r(sum(b.period for b in items), 2), "value": _r(value, 2)})
    site = [b for b in groups.get(None, []) if b.category == cat.SITE]
    others = [b for b in groups.get(None, []) if b.category != cat.SITE]
    for label_key, items in (("site", site), ("general", others)):
        value = sum(b.value for b in items)
        if value <= 0:
            continue
        plan = sum(b.value * b.plan_fraction(on) for b in items) / value * 100
        fact = sum(b.cum for b in items) / value * 100
        finishes = [b.finish for b in items if b.finish]
        rows.append({"building": None, "row": label_key, "plan_finish": max(finishes).isoformat() if finishes else None,
                     "plan_pct": _r(plan, 1), "fact_pct": _r(fact, 1), "gap_pp": _r(fact - plan, 1), "categories": {},
                     "period_value": _r(sum(b.period for b in items), 2), "value": _r(value, 2), "not_started": fact < 0.05})
    return rows


QTY_KINDS = {
    "concrete": (("beton", "бетон", "concrete"), ("m3", "м3", "kubm", "m³")),
    "rebar": (("armatur", "арматур", "rebar", "reinforc"), ("t", "ton", "т", "tn")),
    "masonry": (("horgu", "кладк", "masonry", "brick", "kerpic"), ("m2", "m3", "м2", "м3", "m²", "m³")),
}


def _qty_kind(line: CostLine) -> Optional[str]:
    name = cat._plain(line.name)
    unit = cat._plain(line.unit or "").replace(".", "").replace(" ", "")
    for kind, (words, units) in QTY_KINDS.items():
        if any(w in name for w in words) and (unit in units or any(unit.startswith(u) for u in units if len(u) > 1)):
            return kind
    return None


def _physical(lines: Sequence[CostLine]) -> Dict[str, Any]:
    totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"estimate_qty": 0.0, "cum_qty": 0.0, "cum_value": 0.0})
    per_building: Dict[Tuple[Optional[str], str], Dict[str, float]] = defaultdict(lambda: {"estimate_qty": 0.0, "cum_qty": 0.0, "cum_value": 0.0})
    units: Dict[str, str] = {}
    for line in lines:
        kind = _qty_kind(line)
        if not kind or line.estimate_qty is None:
            continue
        units.setdefault(kind, line.unit or "")
        for bucket in (totals[kind], per_building[(line.building, kind)]):
            bucket["estimate_qty"] += line.estimate_qty or 0.0
            bucket["cum_qty"] += line.cum_qty or 0.0
            bucket["cum_value"] += line.cum_value or 0.0
    rows = []
    for kind in ("concrete", "rebar", "masonry"):
        if kind in totals and totals[kind]["estimate_qty"] > 0:
            t = totals[kind]
            rows.append({"kind": kind, "unit": units.get(kind), "estimate_qty": _r(t["estimate_qty"], 1), "cum_qty": _r(t["cum_qty"], 1),
                         "pct": _r(t["cum_qty"] / t["estimate_qty"] * 100, 1)})
    mismatches = []
    buildings = sorted({b for b, _ in per_building}, key=lambda b: cat.building_sort_key(b))
    for building in buildings:
        rebar = per_building.get((building, "rebar"))
        concrete = per_building.get((building, "concrete"))
        if not rebar or not concrete or rebar["estimate_qty"] <= 0 or concrete["estimate_qty"] <= 0:
            continue
        rebar_pct = rebar["cum_qty"] / rebar["estimate_qty"] * 100
        concrete_pct = concrete["cum_qty"] / concrete["estimate_qty"] * 100
        if rebar_pct >= 50 and concrete_pct <= 5:
            mismatches.append({"building": building, "kind": "rebar_without_concrete", "rebar_pct": _r(rebar_pct, 0),
                               "rebar_qty": _r(rebar["cum_qty"], 0), "rebar_value": _r(rebar["cum_value"], 2),
                               "concrete_pct": _r(concrete_pct, 0), "concrete_qty": _r(concrete["cum_qty"], 0)})
    return {"quantities": rows, "mismatches": mismatches}


def _finance(inp: DelayInput, terms: ContractTerms, cum_ex_vat: float, quality: List[Dict[str, Any]]) -> Dict[str, Any]:
    f3 = _latest_f3(inp.f3)
    vat = terms.vat_rate_pct if terms.vat_rate_pct is not None else DEFAULT_VAT_PCT
    works_vat = f3.works_cum if f3 and f3.works_cum is not None else None
    works_vat_basis = "f3"
    if works_vat is None and cum_ex_vat:
        works_vat = cum_ex_vat * (1 + vat / 100)
        works_vat_basis = "computed"
    advance_received = f3.advance_received if f3 else None
    withheld = f3.advance_withheld_cum if f3 else None
    remaining = f3.advance_remaining if f3 else None
    if remaining is None and advance_received is not None and withheld is not None:
        remaining = advance_received - withheld
    if advance_received is None and not inp.f3:
        quality.append({"code": "f3_missing", "severity": "info",
                        "az": "Forma-3 təqdim edilməyib; avans və ödəniləcək məbləğ göstərilmir.",
                        "en": "No Forma-3 was provided; advance and payable amounts are not shown."})
    value = terms.value_with_vat
    guarantee_end = None
    guarantee_risk = False
    if terms.advance_guarantee_months and terms.signed:
        guarantee_end = _add_months(terms.signed, terms.advance_guarantee_months)
    if remaining and remaining > 0 and guarantee_end:
        report_date = f3.period if f3 and f3.period else None
        guarantee_risk = bool(report_date and guarantee_end <= report_date + timedelta(days=90))
    return {
        "contract_value": _r(value, 2),
        "works_cum_with_vat": _r(works_vat, 2),
        "works_with_vat_basis": works_vat_basis,
        "works_share_of_contract_pct": _r(works_vat / value * 100, 1) if works_vat and value else None,
        "works_period_with_vat": _r(f3.works_period, 2) if f3 else None,
        "advance_received": _r(advance_received, 2),
        "advance_pct": terms.advance_pct,
        "advance_withheld": _r(withheld, 2),
        "advance_withheld_share_pct": _r(withheld / works_vat * 100, 1) if withheld and works_vat else None,
        "advance_remaining": _r(remaining, 2),
        "payable_period": _r(f3.payable_period, 2) if f3 else None,
        "payments_register": None,
        "advance_exceeds_works": bool(advance_received and works_vat and advance_received > works_vat),
        "advance_over_works": _r(advance_received - works_vat, 2) if advance_received and works_vat else None,
        "advance_guarantee_months": terms.advance_guarantee_months,
        "advance_guarantee_end": guarantee_end.isoformat() if guarantee_end else None,
        "advance_guarantee_risk": guarantee_risk,
        "f3_period": f3.period.isoformat() if f3 and f3.period else None,
        "f3_number": f3.number if f3 else None,
    }


# ------------------------------------------------------------------ texts
def _cat_name(category: str, lang: str) -> str:
    return cat.label(category, lang) if category != OTHER else ("Digər işlər" if lang == "az" else "Other works")


def _texts(r: Dict[str, Any]) -> Dict[str, Any]:
    """Key message, key delays, delay cards, actions and decisions (AZ / EN)."""
    out: Dict[str, Any] = {}
    for lang in ("az", "en"):
        out[lang] = _texts_lang(r, lang)
    return out


def _texts_lang(r: Dict[str, Any], lang: str) -> Dict[str, Any]:
    az = lang == "az"
    T = r["totals"]
    F = r["forecast"]
    fin = r["finance"]
    contract = r["contract"]
    report_date = date.fromisoformat(r["report_date"])
    es = date.fromisoformat(T["earned_schedule_date"])
    cats = {row["category"]: row for row in r["categories"]}
    buildings = [b for b in r["buildings"] if b.get("building")]
    finish = date.fromisoformat(contract["finish"]) if contract.get("finish") else None
    money = r["method"] == "estimate_value"

    # Key message.
    days, months = T["delay_days"], T["delay_months"]
    if days > 0:
        head = (f"Tikinti qrafikdən ≈{days} gün (≈{num(months, 1, lang)} ay) geridədir: plan {pct(T['plan_pct'], lang)}, fakt {pct(T['fact_pct'], lang)}."
                if az else f"Construction is ≈{days} days (≈{num(months, 1, lang)} months) behind the schedule: plan {pct(T['plan_pct'], lang)}, actual {pct(T['fact_pct'], lang)}.")
    else:
        head = (f"Tikinti qrafik üzrədir: plan {pct(T['plan_pct'], lang)}, fakt {pct(T['fact_pct'], lang)}."
                if az else f"Construction is on schedule: plan {pct(T['plan_pct'], lang)}, actual {pct(T['fact_pct'], lang)}.")
    tail = ""
    if finish and not F["contract_feasible"]:
        envelope = cats.get(cat.ENVELOPE)
        reason = ""
        if envelope and envelope["fact_pct"] is not None and envelope["fact_pct"] < 5 and envelope["plan_pct"] and envelope["plan_pct"] > 50:
            reason = (" — bina konturunun bağlanması (dam, fasad, pəncərə) praktiki olaraq başlanmayıb" if az
                      else " — closing the building envelope (roof, facade, windows) has practically not started")
        tail = (f" Cari templə müqavilə müddətində ({dmy(finish)}) tamamlanma mümkün deyil{reason}." if az
                else f" At the current pace completion within the contract period ({dmy(finish)}) is not possible{reason}.")
    out: Dict[str, Any] = {"key_message": head + tail, "key_message_head": head, "key_message_tail": tail.strip()}

    # Key delays (bullets).
    bullets: List[Dict[str, str]] = []
    worst = sorted((row for row in r["categories"] if row["gap_pp"] is not None and row["gap_pp"] < -15
                    and row["category"] in (cat.FRAME, cat.MASONRY, cat.ENVELOPE)),
                   key=lambda row: (row["gap_pp"] or 0) * (row["value"] or 0))
    worst = [row for row in worst if row["category"] != cat.FRAME][:2] or worst[:1]
    for row in worst[:2]:
        name = _cat_name(row["category"], lang)
        extra = ""
        if row is worst[0] and money:
            extra = (f" — ən böyük paket, {mln(row['value'], lang)} mln." if az else f" — the largest package, {mln(row['value'], lang)} m.") \
                if row["value"] == max((x["value"] or 0) for x in r["categories"]) else ""
        if row["category"] == cat.MASONRY:
            low = [b["building"] for b in buildings if (b["categories"].get(cat.MASONRY) or 0) <= 3 and b["categories"].get(cat.MASONRY) is not None]
            if low:
                extra = (f" {', '.join(low)}-də hörgü ≈0–3%." if az else f" Masonry in {', '.join(low)} is ≈0–3%.")
        bullets.append({"title": f"{name} — {pct(row['fact_pct'], lang)}",
                        "text": (f"(plan {pct(row['plan_pct'], lang, 0)}){extra}")})
    frame_late = sorted((b for b in buildings if b["categories"].get(cat.FRAME) is not None and b["categories"][cat.FRAME] < 90),
                        key=lambda b: b["categories"][cat.FRAME])
    if frame_late:
        listed = ", ".join(f"{b['building']} ({num(b['categories'][cat.FRAME], 0, lang)}%)" for b in frame_late[:5])
        bullets.append({"title": "Karkas bitməyib:" if az else "Frame not finished:", "text": listed + "."})
    late_groups = [cats[c] for c in (cat.MEP, cat.FINISHING, cat.SITE) if c in cats and (cats[c]["gap_pp"] or 0) < -50]
    if late_groups:
        lo = min(g["fact_pct"] for g in late_groups)
        hi = max(g["fact_pct"] for g in late_groups)
        plo = min(g["plan_pct"] for g in late_groups)
        phi = max(g["plan_pct"] for g in late_groups)
        due = [b for b in buildings if b.get("plan_finish") and date.fromisoformat(b["plan_finish"]) <= report_date]
        short = {cat.MEP: "MEP", cat.FINISHING: "tamamlama" if az else "finishing", cat.SITE: "abadlıq" if az else "site works"}
        names = ", ".join(short[g["category"]] for g in late_groups)
        names = names[0].upper() + names[1:]
        handover = (f"; {len(due)} bina artıq təhvil verilməli idi" if az else f"; {len(due)} buildings should already have been handed over") if due else ""
        bullets.append({"title": f"{names} — {num(lo, 1, lang)}–{pct(hi, lang)}",
                        "text": f"(plan {num(plo, 0, lang)}–{pct(phi, lang, 0)}){handover}."})
    out["key_delays"] = bullets[:4]

    # Delay cards.
    out["delay_cards"] = _delay_cards(r, lang, cats, buildings)

    # Unconfirmed causes.
    obligations = " (müqavilə 12.2 — sifarişçinin öhdəliyi)" if az else " (contract 12.2 — employer's obligation)"
    out["unconfirmed_causes"] = (
        "işçi və texnika çatışmazlığı; material tədarükü; qış şəraiti; layihə/çertyoj dəyişiklikləri; sahəyə giriş icazələri"
        + obligations + ". Təqdim olunmuş sənədlərdə bunların heç biri təsdiq edilmir."
        if az else
        "shortage of labour and plant; material supply; winter conditions; design/drawing changes; site access permits"
        + obligations + ". None of these is confirmed by the documents provided.")

    # Forecast sentences.
    earliest = date.fromisoformat(F["earliest_finish"])
    lines: List[str] = []
    if finish and not F["contract_feasible"]:
        factor = F["required_vs_recent"]
        lines.append(
            (f"Müqavilə müddəti ({dmy(finish)}) reallaşa bilməz" + (f": bunun üçün tempi ≈{num(factor, 0, lang)} dəfə artırmaq lazımdır." if factor else "."))
            if az else
            (f"The contract date ({dmy(finish)}) cannot be met" + (f": the pace would have to rise ≈{num(factor, 0, lang)} times." if factor else ".")))
    sched_factor = F["schedule_vs_recent"]
    lines.append(
        (f"Realist ən tez tarix — {dmy(earliest)}: qalan iş qrafikin öz tempi ilə ({F['plan_remaining_days']} gün) görülərsə."
         + (f" Bu da tempi ≈{num(sched_factor, 0, lang)} dəfə artırmağı tələb edir; qış ayları bu tarixi daha da uzada bilər." if sched_factor and sched_factor > 1.5 else ""))
        if az else
        (f"Realistic earliest date — {dmy(earliest)}: if the remaining work is done at the schedule's own pace ({F['plan_remaining_days']} days)."
         + (f" This also needs a ≈{num(sched_factor, 0, lang)} times higher pace; winter months may push it further." if sched_factor and sched_factor > 1.5 else "")))
    if F["current_pace_unacceptable"]:
        lines.append("Cari templə tarix hesablamaq mənasızdır — bu temp qəbuledilməzdir." if az
                     else "A date at the current pace is meaningless — this pace is unacceptable.")
    elif F["current_pace_finish"]:
        lines.append((f"Son {F['recent_pace_months']} ayın tempi ilə bitmə: {dmy(date.fromisoformat(F['current_pace_finish']))}." if az
                      else f"Finish at the last {F['recent_pace_months']} months' pace: {dmy(date.fromisoformat(F['current_pace_finish']))}."))
    P = r.get("penalty")
    if P:
        cap_txt = ""
        if P.get("cap_pct"):
            cap_txt = ((f", maksimum {num(P['cap_pct'], 0, lang)}%. Limit" + (f" (≈{mln(P['cap_amount'], lang)} mln AZN, müqavilə məbləğindən hesablanırsa)" if P.get("cap_amount") else "")
                        + f" gecikmənin {P['cap_days']}-cü günü" + (f" — ≈{dmy(date.fromisoformat(P['cap_date']))} tarixinə dolur" if P.get("cap_date") else "") + ".")
                       if az else
                       (f", capped at {num(P['cap_pct'], 0, lang)}%. The cap" + (f" (≈{mln(P['cap_amount'], lang)} m AZN if based on the contract value)" if P.get("cap_amount") else "")
                        + f" is reached on day {P['cap_days']} of delay" + (f" — ≈{dmy(date.fromisoformat(P['cap_date']))}" if P.get("cap_date") else "") + "."))
        lines.append((f"Cərimə (müqavilə 28.1): gecikmənin hər günü üçün {num(P['pct_per_day'], 1, lang)}%{cap_txt or '.'} Hesablama bazası hüquqi baxımdan yoxlanılmalıdır."
                      if az else
                      f"Penalty (contract 28.1): {num(P['pct_per_day'], 1, lang)}% per day of delay{cap_txt or '.'} The calculation basis must be checked legally."))
    out["forecast_lines"] = lines

    # Finance notes.
    notes: List[str] = []
    if fin.get("advance_exceeds_works"):
        notes.append((f"Yalnız avans ({mln(fin['advance_received'], lang)} mln) qəbul edilmiş bütün işlərin dəyərindən ({mln(fin['works_cum_with_vat'], lang)} mln) "
                      f"{mln(fin['advance_over_works'], lang)} mln çoxdur — maliyyələşmə fiziki icranı qabaqlayır.")
                     if az else
                     (f"The advance alone ({mln(fin['advance_received'], lang)} m) exceeds the value of all accepted work ({mln(fin['works_cum_with_vat'], lang)} m) "
                      f"by {mln(fin['advance_over_works'], lang)} m — funding is ahead of physical progress."))
    if fin.get("advance_remaining"):
        guarantee = ""
        if fin.get("advance_guarantee_months"):
            guarantee = (f"; 13.1-ə görə təminat müddəti maks. {num(fin['advance_guarantee_months'], 0, lang)} aydır" if az
                         else f"; under 13.1 the guarantee runs for at most {num(fin['advance_guarantee_months'], 0, lang)} months")
        notes.append((f"Avans görülmüş iş sayılmır. Qalıq avans ({mln(fin['advance_remaining'], lang)} mln) bank təminatı ilə örtülməlidir{guarantee}."
                      if az else
                      f"An advance is not work done. The outstanding advance ({mln(fin['advance_remaining'], lang)} m) must be covered by a bank guarantee{guarantee}."))
    if fin.get("advance_guarantee_risk") and fin.get("advance_guarantee_end"):
        end = date.fromisoformat(fin["advance_guarantee_end"])
        notes.append((f"Avans təminatının müddəti {dmy(end)} tarixində bitir/bitib, qalıq avans isə bağlanmayıb — təminatın uzadılması yoxlanılmalıdır."
                      if az else
                      f"The advance guarantee runs out on {dmy(end)} while the advance is not yet recovered — check that it is extended."))
    if fin.get("works_with_vat_basis") == "computed":
        notes.append("F-2 dəyəri (ƏDV ilə) smeta dəyərinə ƏDV əlavə edilərək hesablanıb; Forma-3 təqdim edilməyib." if az
                     else "The F-2 value with VAT is computed by adding VAT; no Forma-3 was provided.")
    out["finance_notes"] = notes

    out["monthly_note"] = _monthly_note(r, lang)
    out["contractor_actions"] = _contractor_actions(r, lang)
    out["director_decisions"] = _director_decisions(r, lang, buildings)
    return out


def pace(F: Dict[str, Any], key: str, lang: str, digits: int = 2) -> str:
    """A pace value with its unit: mln/month, or %/month without an estimate."""
    value = F.get(key)
    if value is None:
        return "—"
    if F.get("pace_unit") == "pct":
        return f"{num(value, 1, lang)}%" + ("/ay" if lang == "az" else "/month")
    return f"{mln(value, lang, digits)} " + ("mln/ay" if lang == "az" else "m/month")


def _monthly_note(r: Dict[str, Any], lang: str) -> str:
    az = lang == "az"
    if r["method"] != "estimate_value":
        return ""
    names = MONTHS_AZ_FULL if az else MONTHS_EN_FULL
    parts: List[str] = []
    missing = [date.fromisoformat(m) for m in r.get("f2_missing_months") or []]
    if missing:
        listed = ", ".join(f"{names[m.month - 1].lower() if az else names[m.month - 1]} {m.year}" for m in missing[:6])
        parts.append(f"{listed} üzrə F-2 aktı yoxdur." if az else f"No F-2 certificate for {listed}.")
    F = r["forecast"]
    if F.get("recent_pace") is not None:
        parts.append((f"Son {F['recent_pace_months']} ayın orta tempi {pace(F, 'recent_pace', lang)}" if az
                      else f"Average pace of the last {F['recent_pace_months']} months: {pace(F, 'recent_pace', lang)}"))
        planned = [(date.fromisoformat(p["month"]), p["plan_value"] or 0) for p in r["monthly"]]
        if planned:
            peak_month, peak = max(planned, key=lambda x: x[1])
            parts[-1] += ((f"; plan tempi ən yüksək {mln(peak, lang)} mln/ay idi ({names[peak_month.month - 1].lower()} {peak_month.year})." if az
                           else f"; the plan peaked at {mln(peak, lang)} m/month ({names[peak_month.month - 1]} {peak_month.year})."))
    acts = [(date.fromisoformat(p["month"]), p.get("f2_value")) for p in r["monthly"] if p.get("f2_value") is not None]
    if len(acts) >= 2 and acts[-1][1] is not None and acts[-2][1]:
        last_m, last_v = acts[-1]
        prev_v = acts[-2][1]
        change = (last_v - prev_v) / prev_v * 100
        if abs(change) >= 20:
            word = ("azdır" if change < 0 else "çoxdur") if az else ("lower" if change < 0 else "higher")
            parts.append((f"{names[last_m.month - 1]} aktı ({mln(last_v, lang)} mln) əvvəlki aydan {num(abs(change), 0, lang)}% {word}." if az
                          else f"The {names[last_m.month - 1]} certificate ({mln(last_v, lang)} m) is {num(abs(change), 0, lang)}% {word} than the month before."))
    return " ".join(parts)


def _delay_cards(r: Dict[str, Any], lang: str, cats: Dict[str, Dict[str, Any]], buildings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    az = lang == "az"
    F = r["forecast"]
    money = r["method"] == "estimate_value"
    cards: List[Dict[str, Any]] = []
    lagging = {row["category"]: row for row in r["categories"] if row["category"] != OTHER and (row["gap_pp"] or 0) < -10}
    # Downstream structural works first (the most visible), then their causes,
    # then the interior works as one card, then site works.
    order = [lagging[c] for c in (cat.ENVELOPE, cat.MASONRY, cat.FRAME, cat.MEP, cat.FINISHING, cat.SITE) if c in lagging]
    used = set()
    impact = {
        cat.ENVELOPE: _t("Bina bağlanmadan daxili bəzək və MEP başlamır; qışda iş itkisi riski.",
                         "Interior finishes and MEP cannot start before the building is closed; risk of lost winter work."),
        cat.MASONRY: _t("Dam/fasad və bütün sonrakı işləri birbaşa ləngidir.", "Directly delays roof/facade and all following works."),
        cat.FRAME: _t("Bu binalarda bütün sonrakı mərhələlər başlamayıb.", "All following stages in these buildings have not started."),
        cat.FINISHING: _t("Binaların təhvili bu işlərdən asılıdır.", "Building handover depends on these works."),
        cat.MEP: _t("Binaların təhvili bu işlərdən asılıdır.", "Building handover depends on these works."),
        cat.SITE: _t("Ərazi hazır olmadan binalar istismara verilə bilməz.", "Buildings cannot be put into use before the site is ready."),
    }
    who = {
        cat.ENVELOPE: _t("Podratçı: dam/fasad briqadaları, pəncərə sifarişi və çatdırılma qrafiki.",
                         "Contractor: roof/facade crews, window orders and delivery schedule."),
        cat.MASONRY: _t("Podratçı: hər binada paralel hörgü cəbhəsi, material ehtiyatının təsdiqi.",
                        "Contractor: parallel masonry fronts in every building, confirmed material stock."),
        cat.FRAME: _t("Podratçı: hər bina üçün karkasın bitmə tarixi və qəlib/kran resursu.",
                      "Contractor: frame completion date for each building and formwork/crane resources."),
        cat.FINISHING: _t("Podratçı: tamamlama briqadalarının sayı və bina üzrə başlama tarixi.",
                          "Contractor: number of finishing crews and start date per building."),
        cat.MEP: _t("Podratçı: MEP subpodratçılarının adı və mobilizasiya tarixi.", "Contractor: MEP subcontractors and mobilisation dates."),
        cat.SITE: _t("Podratçı: abadlıq və xarici şəbəkələr üçün ayrıca qrafik.", "Contractor: a separate programme for site works and external networks."),
    }
    mismatch = {m["building"]: m for m in r["physical"]["mismatches"]}
    for row in order:
        category = row["category"]
        if len(cards) >= 4:
            break
        if category in used:
            continue
        before = cat.DEPENDS_ON.get(category)
        pred = cats.get(before) if before else None
        if category == cat.FRAME:
            late = sorted((b for b in buildings if b["categories"].get(cat.FRAME) is not None and b["categories"][cat.FRAME] < 90),
                          key=lambda b: b["categories"][cat.FRAME])[:3]
            if late:
                numbers = ", ".join(b["building"].replace("Bina-", "") for b in late)
                title = f"Karkas (Bina-{numbers})" if az else f"Frame (Bldg {numbers})"
                figure = " · ".join(f"{num(b['categories'][cat.FRAME], 0, lang)}%" for b in late)
            else:
                title, figure = _cat_name(category, lang), f"{pct(row['fact_pct'], lang)} / plan {pct(row['plan_pct'], lang, 0)}"
            cause = "İzah yoxdur." if az else "No explanation given."
            for b in late:
                m = mismatch.get(b["building"])
                if m:
                    cause += (f" {b['building']}: armaturun {num(m['rebar_pct'], 0, lang)}%-i (≈{num(m['rebar_qty'], 0, lang)} t"
                              + (f", {mln(m['rebar_value'], lang)} mln AZN" if m.get("rebar_value") else "") + f") aktlaşdırılıb, beton isə {num(m['concrete_qty'], 0, lang)} m³ — akt sahədə yoxlanmalıdır."
                              if az else
                              f" {b['building']}: {num(m['rebar_pct'], 0, lang)}% of the rebar (≈{num(m['rebar_qty'], 0, lang)} t) is certified but concrete is {num(m['concrete_qty'], 0, lang)} m³ — check the certificate on site.")
                    break
        elif category in (cat.MEP, cat.FINISHING) and cat.MEP in lagging and cat.FINISHING in lagging:
            group = [lagging[cat.MEP], lagging[cat.FINISHING]]
            used.update({cat.MEP, cat.FINISHING})
            value = sum(g["value"] or 0 for g in group)
            fact_avg = sum((g["fact_pct"] or 0) * (g["value"] or 0) for g in group) / value if value else 0
            plans = [g["plan_pct"] or 0 for g in group]
            title = "MEP, lift, tamamlama" if az else "MEP, lifts, finishing"
            figure = f"≈{pct(fact_avg, lang)} / plan {num(min(plans), 0, lang)}–{pct(max(plans), lang, 0)}"
            envelope = cats.get(cat.ENVELOPE)
            cause = ("Bina konturu bağlanmayıb." if az else "The building envelope is not closed.") \
                if envelope and (envelope["fact_pct"] or 0) < 50 else ("Səbəb göstərilməyib." if az else "No cause given.")
            missing = sorted({q["building"] for q in r["data_quality"] if q.get("code") == "schedule_missing_activities" and q.get("building")},
                             key=cat.building_sort_key)
            if missing:
                cause += (f" Qrafikdə {', '.join(missing)} üçün bəzi fəaliyyətlər yoxdur." if az
                          else f" The schedule lacks some activities for {', '.join(missing)}.")
        else:
            title = _cat_name(category, lang)
            figure = f"{pct(row['fact_pct'], lang)} / plan {pct(row['plan_pct'], lang, 0)}"
            if pred and pred["fact_pct"] is not None and pred["fact_pct"] < 90:
                pred_name = cat.label(before, lang, short=True) if before == cat.FRAME else _cat_name(before, lang)
                cause = (f"{pred_name} bitmədən başlaya bilmir; ayrıca səbəb göstərilməyib." if az
                         else f"Cannot start before the {pred_name.lower()} is finished; no separate cause given.")
            else:
                cause = "Səbəb göstərilməyib." if az else "No cause given."
        effect = impact.get(category, _t("Sonrakı işləri ləngidir.", "Delays the following works."))[lang]
        if category in (cat.MEP, cat.FINISHING) and money:
            rest = sum((cats[c]["remaining_value"] or 0) for c in (cat.MEP, cat.FINISHING) if c in cats)
            remaining_total = r["forecast"]["remaining_value"] or 0
            if rest and remaining_total:
                effect = (f"Qalan dəyərin ≈{num(rest / remaining_total * 100, 0, lang)}%-i ({mln(rest, lang)} mln) bu işlərdədir." if az
                          else f"≈{num(rest / remaining_total * 100, 0, lang)}% of the remaining value ({mln(rest, lang)} m) is in these works.")
        cards.append({"category": category, "title": title, "figure": figure, "cause": cause, "impact": effect,
                      "who": who.get(category, _t("Podratçı: bərpa planı.", "Contractor: recovery plan."))[lang],
                      "severity": row["status"]})
        used.add(category)
    # The overall pace card.
    recent = F["recent_pace"]
    if recent is not None:
        missing = len(r.get("f2_missing_months") or [])
        figure = pace(F, "recent_pace", lang)
        cause = ((f"{missing} ayda F-2 aktı olmayıb; " if missing else "") + "resurs məlumatı təqdim edilməyib.") if az else \
            ((f"No F-2 certificate in {missing} months; " if missing else "") + "no resource data provided.")
        effect = ""
        if F["required_pace"] and recent:
            effect = (f"Müddətdə bitirmək üçün ≈{pace(F, 'required_pace', lang, 1)} lazımdır — cari tempdən ≈{num(F['required_vs_recent'], 0, lang)} dəfə çox."
                      if az else
                      f"Finishing on time needs ≈{pace(F, 'required_pace', lang, 1)} — ≈{num(F['required_vs_recent'], 0, lang)} times the current pace.")
        elif F["contract_feasible"] is False:
            effect = "Müqavilə müddəti artıq keçib." if az else "The contract period has already ended."
        cards.append({"category": "pace", "title": "Ümumi icra tempi" if az else "Overall pace", "figure": figure,
                      "cause": cause[0].upper() + cause[1:], "impact": effect,
                      "who": ("Podratçı: resursla əsaslandırılmış yeni qrafik. Sifarişçi: həftəlik nəzarət." if az
                              else "Contractor: a resource-loaded new programme. Employer: weekly monitoring."),
                      "severity": "critical" if F["current_pace_unacceptable"] else "serious"})
    return cards[:5]


def _contractor_actions(r: Dict[str, Any], lang: str) -> List[Dict[str, str]]:
    az = lang == "az"
    missing = sorted({q["building"] for q in r["data_quality"] if q.get("code") == "schedule_missing_activities" and q.get("building")},
                     key=cat.building_sort_key)
    extra = ""
    if missing:
        extra = (f" {', '.join(missing)} üçün çatışmayan fəaliyyətlər daxil edilsin." if az
                 else f" Add the missing activities for {', '.join(missing)}.")
    if az:
        return [
            {"title": "10 iş günü ərzində yenilənmiş iş qrafiki:", "text": "resurslarla yüklənmiş (işçi, texnika, kran), bina × bölmə üzrə, aylıq F-2 proqnozu ilə." + extra},
            {"title": "Əlavə resurs planı:", "text": "geridə qalan iş növləri üçün ayrıca briqadalar, bina üzrə işçi və texnika sayı."},
            {"title": "Tədarük qrafiki:", "text": "pəncərə-qapı, fasad və dam materialları, lift və MEP avadanlığı üçün sifariş və çatdırılma tarixləri."},
            {"title": "Qış iş planı:", "text": "noyabr–mart dövründə konturun bağlanması və daxili işlərin davamı."},
            {"title": "Həftəlik sahə hesabatı:", "text": "işçi/texnika sayı, görülmüş həcm, fotolar (fiziki icranı F-2-dən ayrı ölçmək üçün)."},
        ]
    return [
        {"title": "Updated programme within 10 working days:", "text": "resource-loaded (labour, plant, cranes), by building × section, with a monthly F-2 forecast." + extra},
        {"title": "Additional resource plan:", "text": "separate crews for the lagging work types, labour and plant per building."},
        {"title": "Procurement schedule:", "text": "order and delivery dates for windows/doors, facade and roof materials, lifts and MEP equipment."},
        {"title": "Winter work plan:", "text": "closing the envelope and continuing interior works from November to March."},
        {"title": "Weekly site report:", "text": "labour/plant numbers, quantities done, photos (to measure physical progress separately from F-2)."},
    ]


def _director_decisions(r: Dict[str, Any], lang: str, buildings: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    az = lang == "az"
    fin = r["finance"]
    contract = r["contract"]
    first = sorted(buildings, key=lambda b: -(b.get("fact_pct") or 0))[:4]
    priority = ", ".join(b["building"].replace("Bina-", "") for b in first)
    advance = fin.get("advance_remaining")
    pay_days = contract.get("payment_days")
    if az:
        return [
            {"title": "Rəsmi xəbərdarlıq:", "text": "podratçıya gecikmə barədə yazılı bildiriş göndərilsin və müqavilə 28.1 üzrə cərimə hüququ qorunsun."},
            {"title": "Avans təminatı:", "text": (f"{mln(advance, 'az')} mln AZN qalıq avansı örtən" if advance else "qalıq avansı örtən")
             + " bank zəmanətinin qüvvədə olduğu yoxlanılsın, lazım olarsa uzadılması tələb edilsin."},
            {"title": "Yeni bitmə tarixi:", "text": "müddətin uzadılması yalnız sənədlə əsaslandırılmış səbəb və resurslu qrafik əsasında baxılsın."
             + (f" Binaların mərhələli təhvil prioriteti müəyyən edilsin (əvvəlcə Bina-{priority})." if priority else "")},
            {"title": "Sifarişçinin öhdəlikləri:", "text": "giriş icazələri (12.2) və aktların " + (f"{num(pay_days, 0, 'az')} iş günü ərzində " if pay_days else "vaxtında ")
             + "ödənilməsi (13.1) yoxlanılsın ki, podratçının iddia əsası qalmasın."},
            {"title": "Nəzarət rejimi:", "text": "texniki nəzarət aylıq fiziki icra % versin; həftəlik iclasda temp və resurs izlənilsin."},
        ]
    return [
        {"title": "Formal notice:", "text": "send the contractor a written delay notice and preserve the right to penalties under clause 28.1."},
        {"title": "Advance guarantee:", "text": (f"check that the bank guarantee covering the {mln(advance, 'en')} m AZN outstanding advance" if advance else "check that the bank guarantee covering the outstanding advance")
         + " is valid and require an extension if needed."},
        {"title": "New completion date:", "text": "consider an extension only on documented causes and a resource-loaded programme."
         + (f" Set a phased handover priority (first Bldg {priority})." if priority else "")},
        {"title": "Employer obligations:", "text": "check site access permits (12.2) and payment of certificates " + (f"within {num(pay_days, 0, 'en')} working days " if pay_days else "on time ")
         + "(13.1) so the contractor has no grounds for a claim."},
        {"title": "Monitoring:", "text": "the supervising engineer should report monthly physical progress %; track pace and resources weekly."},
    ]
