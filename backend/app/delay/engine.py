"""Construction execution and delay analysis engine.

The engine works on calendar days and returns a JSON-safe dictionary
(``schema = "devbareun.delay-analysis/v1"``) that the workspace dashboard and
the PDF/Excel execution report both render.

Method summary (documented for users in docs/DELAY_ANALYSIS_METHOD.md):

* Planned progress of an activity grows linearly between planned start and
  planned finish. Project progress is the weight-averaged activity progress;
  weight = the activity's weight/value column, otherwise its planned duration.
* SPI = actual % / planned % at the data date.
* Schedule delay uses Earned Schedule: the date on the planned S-curve where the
  plan reached today's actual %. Delay = data date - that date.
* Forecast finish per activity: actual finish, a supplied forecast, the current
  production rate (from 20% progress), or the planned rate from the data date. With
  predecessor links, not-started work is pushed by late predecessors (CPM
  forward pass) and total float gives the current critical path.
* Delay events are classified day by day: employer + contractor on the same
  day = concurrent; employer = excusable and compensable; neutral = excusable,
  not compensable; contractor = not excusable.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .model import Activity, DelayEvent, DelayInput

SCHEMA = "devbareun.delay-analysis/v1"
CRITICAL_DELAY_DAYS = 14
NEAR_CRITICAL_WINDOW_DAYS = 7
MIN_PROGRESS_FOR_RATE = 20.0


def _msg(code: str, severity: str, en: str, az: str, **extra: Any) -> Dict[str, Any]:
    item = {"code": code, "severity": severity, "en": en, "az": az}
    item.update(extra)
    return item


def _dmy(value: Optional[str]) -> str:
    """ISO date string -> dd.mm.yyyy for human-readable messages."""
    if not value:
        return "—"
    return f"{value[8:10]}.{value[5:7]}.{value[0:4]}"


def _iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _r(value: Optional[float], digits: int = 1) -> Optional[float]:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    return round(value, digits)


def _month_end(value: date) -> date:
    nxt = date(value.year + (value.month == 12), value.month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def _months_between(start: date, finish: date) -> List[date]:
    months: List[date] = []
    cursor = _month_end(start)
    while cursor <= _month_end(finish):
        months.append(cursor)
        cursor = _month_end(cursor + timedelta(days=1))
    return months


# --------------------------------------------------------------- activities
@dataclass
class _Calc:
    activity: Activity
    duration: int
    weight: float
    progress: float
    forecast_start: date
    forecast_finish: date
    forecast_basis: str
    planned_pct: float = 0.0
    total_float: Optional[int] = None
    critical: bool = False

    @property
    def done(self) -> bool:
        return self.progress >= 100

    @property
    def started(self) -> bool:
        return self.done or self.progress > 0 or self.activity.actual_start is not None


def _planned_pct(activity: Activity, duration: int, on: date) -> float:
    ps, pf = activity.planned_start, activity.planned_finish
    if not ps or not pf or on < ps:
        return 0.0
    if on >= pf:
        return 100.0
    return min(100.0, ((on - ps).days + 1) / duration * 100.0)


def _actual_pct_on(calc: _Calc, on: date, data_date: date) -> float:
    """Reconstructed actual % of one activity on a past date (linear)."""
    act = calc.activity
    start = act.actual_start or (act.planned_start if calc.started else None)
    if not start or on < start or calc.progress <= 0:
        return 0.0
    end = act.actual_finish if (calc.done and act.actual_finish) else data_date
    if on >= end:
        return calc.progress
    span = max(1, (end - start).days + 1)
    return calc.progress * ((on - start).days + 1) / span


def _prepare(inp: DelayInput, data_date: date, quality: List[Dict[str, Any]]) -> Tuple[List[_Calc], List[Activity]]:
    calcs: List[_Calc] = []
    skipped: List[Activity] = []
    for activity in inp.activities:
        if not activity.planned_start or not activity.planned_finish:
            skipped.append(activity)
            continue
        if activity.planned_finish < activity.planned_start:
            activity.planned_start, activity.planned_finish = activity.planned_finish, activity.planned_start
            quality.append(_msg("reversed_dates", "warning",
                                f"{activity.id}: planned finish was before planned start; the dates were swapped.",
                                f"{activity.id}: plan bitişi başlanğıcdan əvvəl idi; tarixlər yerində dəyişdirildi.",
                                activity_id=activity.id))
        duration = max(1, (activity.planned_finish - activity.planned_start).days + 1)
        progress = activity.progress
        if progress is None:
            progress = 100.0 if activity.actual_finish else 0.0
        if activity.actual_finish and progress < 100:
            progress = 100.0
        if progress >= 100 and not activity.actual_finish:
            quality.append(_msg("complete_without_finish", "info",
                                f"{activity.id}: 100% complete but no actual finish date; the data date is used.",
                                f"{activity.id}: 100% icra olunub, amma faktiki bitmə tarixi yoxdur; hesabat tarixi götürüldü.",
                                activity_id=activity.id))
        if progress > 0 and not activity.actual_start and activity.planned_start > data_date:
            quality.append(_msg("progress_before_start", "warning",
                                f"{activity.id}: progress reported before its planned start and without an actual start date.",
                                f"{activity.id}: plan başlanğıcından əvvəl icra göstərilib, faktiki başlanğıc tarixi yoxdur.",
                                activity_id=activity.id))
        for label, value in (("actual start", activity.actual_start), ("actual finish", activity.actual_finish)):
            if value and value > data_date:
                quality.append(_msg("actual_after_data_date", "warning",
                                    f"{activity.id}: {label} {value.isoformat()} is after the data date.",
                                    f"{activity.id}: faktiki tarix {value.isoformat()} hesabat tarixindən sonradır.",
                                    activity_id=activity.id))
        weight = activity.weight if activity.weight and activity.weight > 0 else float(duration)
        calcs.append(_Calc(activity=activity, duration=duration, weight=weight, progress=progress,
                           forecast_start=activity.planned_start, forecast_finish=activity.planned_finish,
                           forecast_basis="plan"))
    return calcs, skipped


def _forecast(calc: _Calc, data_date: date, quality: List[Dict[str, Any]]) -> None:
    act = calc.activity
    ps = act.planned_start
    assert ps is not None
    if calc.done:
        calc.forecast_start = act.actual_start or ps
        calc.forecast_finish = act.actual_finish or data_date
        calc.forecast_basis = "actual"
        return
    if calc.started:
        calc.forecast_start = act.actual_start or min(ps, data_date)
        if act.forecast_finish and act.forecast_finish >= data_date:
            calc.forecast_finish = act.forecast_finish
            calc.forecast_basis = "reported_forecast"
            return
        if 0 < calc.progress < MIN_PROGRESS_FOR_RATE:
            # Early in an activity the measured rate is noisy; the remaining
            # work is assumed to run at the planned rate from the data date.
            remaining = math.ceil(calc.duration * (100.0 - calc.progress) / 100.0)
            calc.forecast_finish = data_date + timedelta(days=remaining)
            calc.forecast_basis = "planned_rate"
            return
        if calc.progress > 0:
            elapsed = max(1, (data_date - calc.forecast_start).days + 1)
            rate = calc.progress / elapsed
            remaining = math.ceil((100.0 - calc.progress) / rate)
            cap = calc.duration * 3
            if remaining > cap:
                remaining = cap
                quality.append(_msg("rate_capped", "info",
                                    f"{act.id}: very low production rate; remaining time capped at 3x planned duration.",
                                    f"{act.id}: icra sürəti çox aşağıdır; qalan müddət plan müddətinin 3 misli ilə məhdudlaşdırıldı.",
                                    activity_id=act.id))
            calc.forecast_finish = data_date + timedelta(days=remaining)
            calc.forecast_basis = "production_rate"
            return
        calc.forecast_finish = data_date + timedelta(days=calc.duration)
        calc.forecast_basis = "planned_duration"
        return
    # Not started
    if act.forecast_finish and act.forecast_finish >= data_date:
        calc.forecast_finish = act.forecast_finish
        calc.forecast_start = max(ps, act.forecast_finish - timedelta(days=calc.duration - 1))
        calc.forecast_basis = "reported_forecast"
        return
    start = ps if ps > data_date else data_date + timedelta(days=1)
    calc.forecast_start = start
    calc.forecast_finish = start + timedelta(days=calc.duration - 1)
    calc.forecast_basis = "plan" if ps > data_date else "late_start"


def _topological(calcs: List[_Calc], quality: List[Dict[str, Any]]) -> Optional[List[_Calc]]:
    by_id = {c.activity.id: c for c in calcs}
    indegree: Dict[str, int] = {c.activity.id: 0 for c in calcs}
    successors: Dict[str, List[str]] = defaultdict(list)
    unknown: Set[str] = set()
    for c in calcs:
        for pred in c.activity.predecessors:
            if pred in by_id and pred != c.activity.id:
                successors[pred].append(c.activity.id)
                indegree[c.activity.id] += 1
            elif pred not in by_id:
                unknown.add(pred)
    if unknown:
        sample = ", ".join(sorted(unknown)[:5])
        quality.append(_msg("unknown_predecessor", "warning",
                            f"Predecessor IDs not found in the schedule and ignored: {sample}.",
                            f"İş qrafikində tapılmayan öncül iş kodları nəzərə alınmadı: {sample}."))
    queue = [k for k, v in indegree.items() if v == 0]
    order: List[_Calc] = []
    while queue:
        key = queue.pop(0)
        order.append(by_id[key])
        for succ in successors[key]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)
    if len(order) != len(calcs):
        quality.append(_msg("logic_loop", "warning",
                            "The predecessor links contain a loop; network logic was not used for the forecast.",
                            "Öncül iş əlaqələrində dövr (loop) var; proqnozda şəbəkə məntiqi istifadə olunmadı."))
        return None
    return order


def _apply_network(order: List[_Calc], data_date: date, project_finish: date) -> None:
    by_id = {c.activity.id: c for c in order}
    for calc in order:
        preds = [by_id[p] for p in calc.activity.predecessors if p in by_id]
        if not preds or calc.started:
            continue
        earliest = max(p.forecast_finish for p in preds) + timedelta(days=1)
        if earliest > calc.forecast_start:
            calc.forecast_start = earliest
            calc.forecast_finish = earliest + timedelta(days=calc.duration - 1)
            calc.forecast_basis = "network"
    # Backward pass on the forecast network -> total float.
    successors: Dict[str, List[_Calc]] = defaultdict(list)
    for calc in order:
        for p in calc.activity.predecessors:
            if p in by_id:
                successors[p].append(calc)
    late_finish: Dict[str, date] = {}
    end = max([project_finish] + [c.forecast_finish for c in order])
    for calc in reversed(order):
        # A successor that already started is out of sequence: progress
        # overrides the logic, so it no longer constrains this activity.
        succ = [s for s in successors.get(calc.activity.id) or [] if not s.started or calc.done]
        if succ:
            late = min(late_finish[s.activity.id] - timedelta(days=(s.forecast_finish - s.forecast_start).days + 1) for s in succ)
        else:
            late = end
        late_finish[calc.activity.id] = late
        calc.total_float = (late - calc.forecast_finish).days
        # Completed activities with zero float form the as-built driving path,
        # which is what past delay events are measured against.
        calc.critical = calc.total_float <= 0


def _weighted(calcs: Sequence[_Calc], values: Iterable[float]) -> float:
    total = sum(c.weight for c in calcs)
    if total <= 0:
        return 0.0
    return sum(c.weight * v for c, v in zip(calcs, values)) / total


def _planned_curve(calcs: Sequence[_Calc], on: date) -> float:
    return _weighted(calcs, (_planned_pct(c.activity, c.duration, on) for c in calcs))


def _earned_schedule_date(calcs: Sequence[_Calc], actual: float, start: date, finish: date) -> date:
    """First date on which the planned S-curve reaches ``actual`` percent."""
    if actual <= 0:
        return start - timedelta(days=1)
    lo, hi = 0, (finish - start).days
    if _planned_curve(calcs, finish) < actual:
        return finish
    while lo < hi:
        mid = (lo + hi) // 2
        if _planned_curve(calcs, start + timedelta(days=mid)) >= actual - 1e-9:
            hi = mid
        else:
            lo = mid + 1
    return start + timedelta(days=lo)


def _status(calc: _Calc, data_date: date) -> str:
    """completed | completed_late | on_track | not_started | late_start |
    delayed (<= 14 days) | major_delay (> 14 days) | critical_delay (on the
    critical path and late)."""
    pf = calc.activity.planned_finish
    ps = calc.activity.planned_start
    assert pf is not None and ps is not None
    variance = (calc.forecast_finish - pf).days
    if calc.done:
        return "completed_late" if variance > 0 else "completed"
    if variance <= 0:
        return "on_track" if calc.started else ("late_start" if ps < data_date else "not_started")
    if calc.critical:
        return "critical_delay"
    if variance > CRITICAL_DELAY_DAYS:
        return "major_delay"
    if not calc.started and ps < data_date:
        return "late_start"
    return "delayed"


DELAYED_STATUSES = {"delayed", "major_delay", "critical_delay", "late_start", "completed_late"}


# ------------------------------------------------------------- delay events
def _event_days(event: DelayEvent, data_date: date) -> Set[date]:
    if not event.start:
        return set()
    finish = event.finish or data_date
    if finish < event.start:
        finish = event.start
    return {event.start + timedelta(days=i) for i in range((finish - event.start).days + 1)}


def _analyse_events(events: List[DelayEvent], calcs: List[_Calc], data_date: date, critical_ids: Set[str],
                    quality: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not events:
        return {"available": False}
    known_ids = {c.activity.id for c in calcs}
    party_days: Dict[str, Set[date]] = {"employer": set(), "contractor": set(), "neutral": set()}
    critical_party_days: Dict[str, Set[date]] = {"employer": set(), "contractor": set(), "neutral": set()}
    rows: List[Dict[str, Any]] = []
    causes: Dict[str, Dict[str, Any]] = {}
    unassigned_days = 0
    for event in events:
        days = _event_days(event, data_date)
        if not days:
            quality.append(_msg("event_without_dates", "warning",
                                f"Delay event {event.id} has no start date and was not counted.",
                                f"{event.id} gecikmə hadisəsinin başlanğıc tarixi yoxdur, hesaba alınmadı.",
                                event_id=event.id))
        affected = [a for a in event.activity_ids if a in known_ids]
        missing = [a for a in event.activity_ids if a not in known_ids]
        if missing:
            quality.append(_msg("event_unknown_activity", "info",
                                f"Delay event {event.id} refers to activities not in the schedule: {', '.join(missing[:5])}.",
                                f"{event.id} hadisəsi qrafikdə olmayan işlərə istinad edir: {', '.join(missing[:5])}.",
                                event_id=event.id))
        on_critical = bool(set(affected) & critical_ids) if affected else None
        party = event.responsible
        if party in party_days:
            party_days[party] |= days
            if on_critical or on_critical is None:
                critical_party_days[party] |= days
        else:
            unassigned_days += len(days)
        cause = event.cause or "Unspecified"
        bucket = causes.setdefault(cause, {"cause": cause, "events": 0, "days": 0})
        bucket["events"] += 1
        bucket["days"] += len(days)
        rows.append({
            "id": event.id,
            "description": event.description,
            "start": _iso(event.start),
            "finish": _iso(event.finish),
            "ongoing": bool(event.start and not event.finish),
            "days": len(days),
            "cause": event.cause,
            "responsible": party or "unassigned",
            "activity_ids": event.activity_ids,
            "affects_critical_path": on_critical,
            "notes": event.notes,
        })

    def classify(sets: Dict[str, Set[date]]) -> Dict[str, int]:
        all_days = sets["employer"] | sets["contractor"] | sets["neutral"]
        result = {"employer": 0, "contractor": 0, "neutral": 0, "concurrent": 0}
        for day in all_days:
            e, c, n = day in sets["employer"], day in sets["contractor"], day in sets["neutral"]
            if e and c:
                result["concurrent"] += 1
            elif e:
                result["employer"] += 1
            elif n:
                result["neutral"] += 1
            else:
                result["contractor"] += 1
        result["total"] = len(all_days)
        result["excusable"] = result["employer"] + result["neutral"] + result["concurrent"]
        result["compensable"] = result["employer"]
        result["non_excusable"] = result["contractor"]
        return result

    rows.sort(key=lambda r: (-(r["days"] or 0), r["id"]))
    return {
        "available": True,
        "count": len(events),
        "events": rows,
        "by_party_days": classify(party_days),
        "critical_by_party_days": classify(critical_party_days),
        "unassigned_days": unassigned_days,
        "by_cause": sorted(causes.values(), key=lambda c: -c["days"]),
    }


# ------------------------------------------------------------------ summary
def _wbs_summary(calcs: List[_Calc], data_date: date) -> List[Dict[str, Any]]:
    groups: Dict[str, List[_Calc]] = defaultdict(list)
    for calc in calcs:
        groups[calc.activity.wbs or "—"].append(calc)
    if len(groups) <= 1 and "—" in groups:
        return []
    rows = []
    for name, items in groups.items():
        planned = _weighted(items, (c.planned_pct for c in items))
        actual = _weighted(items, (c.progress for c in items))
        pf = max(c.activity.planned_finish for c in items if c.activity.planned_finish)
        ff = max(c.forecast_finish for c in items)
        rows.append({
            "wbs": name,
            "activities": len(items),
            "weight_share": None,
            "planned_pct": _r(planned),
            "actual_pct": _r(actual),
            "spi": _r(actual / planned, 2) if planned > 0 else None,
            "planned_finish": _iso(pf),
            "forecast_finish": _iso(ff),
            "finish_variance_days": (ff - pf).days,
            "delayed_activities": sum(1 for c in items if _status(c, data_date) in DELAYED_STATUSES),
            "_weight": sum(c.weight for c in items),
        })
    total = sum(r["_weight"] for r in rows) or 1
    for row in rows:
        row["weight_share"] = _r(row.pop("_weight") / total * 100)
    rows.sort(key=lambda r: (-r["finish_variance_days"], r["wbs"]))
    return rows


def _monthly(calcs: List[_Calc], inp: DelayInput, start: date, planned_finish: date, forecast_finish: date,
             data_date: date) -> Tuple[List[Dict[str, Any]], str]:
    supplied = {_month_end(m.period): m for m in inp.monthly}
    months = _months_between(start, max(planned_finish, forecast_finish, data_date))
    actual_source = "supplied" if any(m.actual is not None for m in inp.monthly) else "reconstructed"
    rows: List[Dict[str, Any]] = []
    previous_delay: Optional[int] = None
    for month in months:
        planned = _planned_curve(calcs, month)
        if month in supplied and supplied[month].planned is not None:
            planned = supplied[month].planned or 0.0
        actual: Optional[float] = None
        point = min(month, data_date)
        if month <= _month_end(data_date):
            if actual_source == "supplied":
                actual = supplied[month].actual if month in supplied else None
            else:
                actual = _weighted(calcs, (_actual_pct_on(c, point, data_date) for c in calcs))
        delay: Optional[int] = None
        if actual is not None:
            es = _earned_schedule_date(calcs, actual, start, planned_finish)
            delay = max(0, (point - es).days) if actual < 100 else max(0, (min(point, data_date) - planned_finish).days)
        rows.append({
            "month": month.strftime("%Y-%m"),
            "month_end": month.isoformat(),
            "planned_cumulative_pct": _r(planned),
            "actual_cumulative_pct": _r(actual),
            "schedule_delay_days": delay,
            "delay_change_days": (delay - previous_delay) if (delay is not None and previous_delay is not None) else delay,
        })
        if delay is not None:
            previous_delay = delay
    return rows, actual_source


def _overall_status(forecast_delay: int, spi: Optional[float]) -> str:
    if forecast_delay <= 0 and (spi is None or spi >= 0.95):
        return "on_track"
    if forecast_delay <= 30 and (spi is None or spi >= 0.85):
        return "at_risk"
    return "critical"


def _findings(kpis: Dict[str, Any], top: List[Dict[str, Any]], wbs: List[Dict[str, Any]], events: Dict[str, Any],
              critical_method: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    findings: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    delay = kpis["forecast_delay_days"]
    spi = kpis["spi"]
    findings.append(_msg("progress", "info",
                         f"Actual progress is {kpis['actual_progress_pct']}% against {kpis['planned_progress_pct']}% planned at the data date (SPI {spi}).",
                         f"Hesabat tarixinə faktiki icra {kpis['actual_progress_pct']}%, plan isə {kpis['planned_progress_pct']}% təşkil edir (SPI {spi})."))
    if kpis["schedule_delay_days"] > 0:
        findings.append(_msg("schedule_delay", "warning",
                             f"The works are {kpis['schedule_delay_days']} days behind the baseline programme (earned schedule).",
                             f"İşlər əsas iş qrafikindən {kpis['schedule_delay_days']} gün geri qalır (earned schedule)."))
    if delay > 0:
        findings.append(_msg("forecast_delay", "critical" if delay > 30 else "warning",
                             f"Forecast completion is {_dmy(kpis['forecast_finish'])}, {delay} days after the planned completion {_dmy(kpis['planned_finish'])}.",
                             f"Proqnozlaşdırılan bitmə tarixi {_dmy(kpis['forecast_finish'])}, planlaşdırılmış {_dmy(kpis['planned_finish'])} tarixindən {delay} gün gecdir."))
    else:
        findings.append(_msg("forecast_on_time", "good",
                             f"Forecast completion {_dmy(kpis['forecast_finish'])} is within the planned completion {_dmy(kpis['planned_finish'])}.",
                             f"Proqnozlaşdırılan bitmə tarixi {_dmy(kpis['forecast_finish'])} plan bitmə tarixi {_dmy(kpis['planned_finish'])} daxilindədir."))
    started_sections = [w for w in wbs if (w["planned_pct"] or 0) > 0]
    if started_sections:
        worst = started_sections[0]
        if worst["finish_variance_days"] > 0:
            findings.append(_msg("worst_section", "warning",
                                 f"The most delayed section is '{worst['wbs']}' (+{worst['finish_variance_days']} days, {worst['actual_pct']}% vs {worst['planned_pct']}% planned).",
                                 f"Ən çox gecikən bölmə '{worst['wbs']}' (+{worst['finish_variance_days']} gün, faktiki {worst['actual_pct']}%, plan {worst['planned_pct']}%)."))
    if top:
        names = ", ".join(f"{t['id']} {t['name']}" for t in top[:3])
        findings.append(_msg("top_delays", "warning",
                             f"Largest activity delays: {names}.",
                             f"Ən böyük gecikmələr: {names}."))
    if events.get("available"):
        parties = events["by_party_days"]
        findings.append(_msg("responsibility", "info",
                             f"Recorded delay events: employer {parties['employer']} days, contractor {parties['contractor']} days, neutral {parties['neutral']} days, concurrent {parties['concurrent']} days.",
                             f"Qeydə alınmış gecikmə hadisələri: sifarişçi {parties['employer']} gün, podratçı {parties['contractor']} gün, neytral {parties['neutral']} gün, eyni vaxtda (concurrent) {parties['concurrent']} gün."))
        excusable = events["critical_by_party_days"]["excusable"]
        if excusable > 0:
            actions.append(_msg("eot", "high",
                                f"Prepare an extension of time (EOT) notice for up to {excusable} excusable days on the critical path, with event records attached.",
                                f"Kritik yolda {excusable} günə qədər üzrlü gecikmə üçün müddətin uzadılması (EOT) bildirişi hazırlayın, hadisə sənədlərini əlavə edin."))
        if events["critical_by_party_days"]["compensable"] > 0:
            actions.append(_msg("compensation", "medium",
                                f"{events['critical_by_party_days']['compensable']} employer-caused days may also support a cost claim; collect cost records for those dates.",
                                f"Sifarişçi səbəbli {events['critical_by_party_days']['compensable']} gün xərc tələbi üçün də əsas ola bilər; həmin tarixlər üzrə xərc sənədlərini toplayın."))
        if delay > 0 and events["by_party_days"]["total"] < delay:
            gap = delay - events["by_party_days"]["total"]
            actions.append(_msg("unexplained", "medium",
                                f"{gap} days of forecast delay are not explained by any recorded event; record their causes.",
                                f"Proqnoz gecikmənin {gap} günü heç bir qeydə alınmış hadisə ilə izah olunmur; səbəblərini qeyd edin."))
    elif delay > 0:
        actions.append(_msg("record_events", "high",
                            "No delay events were supplied. Record each delay event with dates, cause and responsible party to support any extension of time.",
                            "Gecikmə hadisələri təqdim olunmayıb. Müddətin uzadılmasını əsaslandırmaq üçün hər hadisəni tarix, səbəb və məsul tərəflə qeyd edin."))
    if delay > 0:
        crit = [t for t in top if t.get("critical")][:3] or top[:3]
        if crit:
            ids = ", ".join(t["id"] for t in crit)
            actions.append(_msg("recovery", "high",
                                f"Prepare a recovery programme for {ids}: added crews, extended shifts or re-sequencing, with a weekly target.",
                                f"{ids} işləri üçün bərpa (recovery) qrafiki hazırlayın: əlavə briqada, uzadılmış növbə və ya ardıcıllığın dəyişdirilməsi, həftəlik hədəflə."))
    if spi is not None and spi < 0.9:
        actions.append(_msg("production_rate", "medium",
                            f"SPI {spi} means work is produced at {round(spi * 100)}% of the planned rate; review resources against the plan.",
                            f"SPI {spi} işlərin plan sürətinin {round(spi * 100)}%-i ilə getdiyini göstərir; resursları planla müqayisə edin."))
    if critical_method == "approximate":
        actions.append(_msg("add_logic", "low",
                            "Add predecessor links to the schedule to get a true critical path and float.",
                            "Həqiqi kritik yol və ehtiyat vaxtı (float) üçün iş qrafikinə öncül iş əlaqələrini əlavə edin."))
    return findings, actions


# --------------------------------------------------------------------- main
def analyze(inp: DelayInput, *, today: Optional[date] = None) -> Dict[str, Any]:
    quality: List[Dict[str, Any]] = [
        _msg("reader_warning", "warning", text, text) for text in inp.warnings
    ]
    today = today or date.today()
    info = inp.project

    actual_dates = [d for a in inp.activities for d in (a.actual_start, a.actual_finish) if d]
    if info.data_date:
        data_date, data_date_source = info.data_date, "supplied"
    elif actual_dates:
        data_date, data_date_source = max(actual_dates), "latest_actual"
        quality.append(_msg("data_date_inferred", "info",
                            f"No data date given; the latest actual date {_dmy(data_date.isoformat())} is used.",
                            f"Hesabat tarixi verilməyib; ən son faktiki tarix {_dmy(data_date.isoformat())} götürüldü."))
    else:
        data_date, data_date_source = today, "today"
        quality.append(_msg("data_date_today", "warning",
                            "No data date or actual dates given; today's date is used.",
                            "Hesabat tarixi və faktiki tarixlər verilməyib; bugünkü tarix götürüldü."))

    calcs, skipped = _prepare(inp, data_date, quality)
    if skipped:
        ids = ", ".join(a.id for a in skipped[:8])
        quality.append(_msg("missing_plan_dates", "warning",
                            f"{len(skipped)} activities have no planned start/finish and were excluded: {ids}.",
                            f"{len(skipped)} işin plan başlanğıc/bitmə tarixi yoxdur və hesaba alınmadı: {ids}."))
    if not calcs:
        return {
            "schema": SCHEMA,
            "ok": False,
            "error": {
                "en": "No activities with planned start and finish dates were found. Use the DevBareun delay analysis template or a schedule export (Excel, CSV, XER, MS Project XML).",
                "az": "Plan başlanğıc və bitmə tarixi olan iş tapılmadı. DevBareun gecikmə analizi şablonundan və ya iş qrafiki ixracından (Excel, CSV, XER, MS Project XML) istifadə edin.",
            },
            "data_quality": quality,
            "sources": inp.sources,
        }
    if not any(a.progress is not None or a.actual_start or a.actual_finish for a in inp.activities):
        quality.append(_msg("no_actuals", "critical",
                            "No actual progress or actual dates were found; the analysis shows the plan only.",
                            "Faktiki icra və ya faktiki tarix tapılmadı; analiz yalnız planı göstərir."))

    project_start = min(c.activity.planned_start for c in calcs if c.activity.planned_start)
    schedule_finish = max(c.activity.planned_finish for c in calcs if c.activity.planned_finish)
    if info.contract_start and info.contract_start < project_start:
        project_start = info.contract_start
    planned_finish = info.contract_finish or schedule_finish
    if info.contract_finish and abs((info.contract_finish - schedule_finish).days) > 1:
        quality.append(_msg("contract_vs_schedule", "info",
                            f"Contract completion {info.contract_finish.isoformat()} differs from the last planned activity finish {schedule_finish.isoformat()}; the contract date is used for delay.",
                            f"Müqavilə bitmə tarixi {info.contract_finish.isoformat()} qrafikdəki son plan bitmə tarixindən {schedule_finish.isoformat()} fərqlidir; gecikmə müqavilə tarixinə görə hesablandı.",
                            ))

    for calc in calcs:
        calc.planned_pct = _planned_pct(calc.activity, calc.duration, data_date)
        _forecast(calc, data_date, quality)

    linked = sum(1 for c in calcs if c.activity.predecessors)
    critical_method = "approximate"
    if linked >= max(1, len(calcs) // 3):
        order = _topological(calcs, quality)
        if order is not None:
            _apply_network(order, data_date, planned_finish)
            critical_method = "cpm"
    forecast_finish = max(c.forecast_finish for c in calcs)
    if critical_method == "approximate":
        for calc in calcs:
            if not calc.done:
                calc.total_float = (forecast_finish - calc.forecast_finish).days
                calc.critical = calc.total_float <= NEAR_CRITICAL_WINDOW_DAYS

    planned_pct = _weighted(calcs, (c.planned_pct for c in calcs))
    actual_pct = _weighted(calcs, (c.progress for c in calcs))
    spi = actual_pct / planned_pct if planned_pct > 0 else None
    es_date = _earned_schedule_date(calcs, actual_pct, project_start, schedule_finish)
    schedule_delay = max(0, (data_date - es_date).days) if actual_pct < 100 else 0
    elapsed = max(1, (data_date - project_start).days + 1)
    earned_days = max(0, (es_date - project_start).days + 1)
    spi_t = earned_days / elapsed if data_date >= project_start else None
    planned_days = (planned_finish - project_start).days + 1
    spi_forecast = (project_start + timedelta(days=math.ceil(planned_days / spi_t) - 1)) if spi_t and spi_t > 0.05 and actual_pct < 100 else None
    forecast_delay = (forecast_finish - planned_finish).days
    time_elapsed_pct = min(100.0, max(0.0, elapsed / planned_days * 100))

    activity_rows: List[Dict[str, Any]] = []
    for calc in calcs:
        act = calc.activity
        assert act.planned_start and act.planned_finish
        start_ref = act.actual_start or calc.forecast_start
        activity_rows.append({
            "id": act.id,
            "name": act.name,
            "wbs": act.wbs,
            "planned_start": _iso(act.planned_start),
            "planned_finish": _iso(act.planned_finish),
            "planned_duration_days": calc.duration,
            "actual_start": _iso(act.actual_start),
            "actual_finish": _iso(act.actual_finish),
            "forecast_start": _iso(calc.forecast_start),
            "forecast_finish": _iso(calc.forecast_finish),
            "forecast_basis": calc.forecast_basis,
            "planned_pct": _r(calc.planned_pct),
            "actual_pct": _r(calc.progress),
            "progress_gap_pct": _r(calc.progress - calc.planned_pct),
            "start_variance_days": (start_ref - act.planned_start).days,
            "finish_variance_days": (calc.forecast_finish - act.planned_finish).days,
            "total_float_days": calc.total_float,
            "critical": calc.critical,
            "status": _status(calc, data_date),
            "weight": _r(calc.weight, 2),
            "predecessors": act.predecessors,
        })
    activity_rows.sort(key=lambda r: (r["planned_start"] or "", r["id"]))
    delayed_rows = sorted((r for r in activity_rows if r["finish_variance_days"] > 0),
                          key=lambda r: (-r["finish_variance_days"], r["id"]))
    status_counts: Dict[str, int] = defaultdict(int)
    for row in activity_rows:
        status_counts[row["status"]] += 1

    critical_ids = {c.activity.id for c in calcs if c.critical}
    events = _analyse_events(inp.events, calcs, data_date, critical_ids, quality)
    wbs = _wbs_summary(calcs, data_date)
    monthly, actual_source = _monthly(calcs, inp, project_start, planned_finish, forecast_finish, data_date)

    kpis = {
        "data_date": data_date.isoformat(),
        "data_date_source": data_date_source,
        "project_start": project_start.isoformat(),
        "planned_finish": planned_finish.isoformat(),
        "forecast_finish": forecast_finish.isoformat(),
        "forecast_finish_spi": _iso(spi_forecast),
        "forecast_delay_days": forecast_delay,
        "schedule_delay_days": schedule_delay,
        "earned_schedule_date": es_date.isoformat() if actual_pct > 0 else None,
        "planned_progress_pct": _r(planned_pct),
        "actual_progress_pct": _r(actual_pct),
        "progress_gap_pct": _r(actual_pct - planned_pct),
        "spi": _r(spi, 2),
        "spi_t": _r(spi_t, 2),
        "time_elapsed_pct": _r(time_elapsed_pct),
        "planned_duration_days": planned_days,
        "forecast_duration_days": (forecast_finish - project_start).days + 1,
        "activities_total": len(calcs),
        "activities_completed": status_counts["completed"] + status_counts["completed_late"],
        "activities_in_progress": sum(1 for r in activity_rows if 0 < (r["actual_pct"] or 0) < 100),
        "activities_delayed": len(delayed_rows),
        "activities_critical": sum(1 for c in calcs if c.critical and not c.done),
        "status": _overall_status(forecast_delay, _r(spi, 2)),
    }
    findings, actions = _findings(kpis, delayed_rows[:10] if delayed_rows else [], wbs, events, critical_method)

    return {
        "schema": SCHEMA,
        "ok": True,
        "project": {
            "name": info.name,
            "client": info.client,
            "contractor": info.contractor,
            "location": info.location,
            "contract_start": _iso(info.contract_start),
            "contract_finish": _iso(info.contract_finish),
            "currency": info.currency,
        },
        "kpis": kpis,
        "status_counts": dict(status_counts),
        "critical_path": {
            "method": critical_method,
            "activities": [r for r in activity_rows if r["critical"]],
        },
        "top_delays": delayed_rows[:10],
        "activities": activity_rows,
        "wbs": wbs,
        "monthly": monthly,
        "monthly_actual_source": actual_source,
        "events": events,
        "findings": findings,
        "actions": actions,
        "data_quality": quality,
        "sources": sorted(set(inp.sources)),
        "method": {
            "calendar": "calendar_days",
            "weights": "weight_column" if any(a.weight for a in inp.activities) else "planned_duration",
            "critical_path": critical_method,
            "critical_delay_threshold_days": CRITICAL_DELAY_DAYS,
        },
    }
