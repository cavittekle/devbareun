"""Fictional residential estate used by the public example and the template.

Six buildings, a schedule by building and work type, estimate (smeta) lines
with cumulative F-2 values, monthly F-2 totals, a Forma-3 and the key contract
terms. All names and numbers are invented.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from . import categories as cat
from .model import (Activity, ContractTerms, CostLine, DelayEvent, DelayInput, F3Summary, PaymentCertificate,
                    ProjectInfo)

D = date
NAME = "Nümunə yaşayış massivi, 1-ci mərhələ (6 bina)"
CLIENT = "Nümunə Sifarişçi PHŞ"
CONTRACTOR = "Nümunə Podratçı MMC"
REPORT_DATE = D(2026, 10, 31)
SIGNED = D(2025, 9, 15)
START = D(2025, 10, 1)
FINISH = D(2027, 1, 15)
VAT = 0.18

BUILDINGS = ["Bina-1", "Bina-2", "Bina-3", "Bina-4", "Bina-5", "Bina-6"]

# (category, section name, line name, unit, quantity, value AZN before VAT)
LINES_PER_BUILDING: List[Tuple[str, str, str, str, float, float]] = [
    (cat.FRAME, "Torpaq işləri", "Qazıntı və geri doldurma", "m3", 6_200, 140_000),
    (cat.FRAME, "Dəmir-beton karkas", "Beton B25 (özül, sütun, plitə)", "m3", 4_100, 620_000),
    (cat.FRAME, "Dəmir-beton karkas", "Armatur A500C", "t", 430, 470_000),
    (cat.MASONRY, "Hörgü işləri", "Əhəng daşından divar hörgüsü", "m2", 9_800, 290_000),
    (cat.ENVELOPE, "Dam örtüyü", "Dam örtüyü və izolyasiya", "m2", 1_450, 360_000),
    (cat.ENVELOPE, "Fasad", "Fasad üzlüyü", "m2", 6_300, 690_000),
    (cat.ENVELOPE, "Qapı-pəncərə", "Pəncərə və vitraj blokları", "m2", 1_250, 420_000),
    (cat.FINISHING, "Daxili bəzək", "Suvaq, döşəmə, boya işləri", "m2", 18_500, 820_000),
    (cat.MEP, "Mühəndis sistemləri", "Su təchizatı, kanalizasiya, istilik", "kompl", 1, 420_000),
    (cat.MEP, "Mühəndis sistemləri", "Elektrik və zəif cərəyan", "kompl", 1, 260_000),
    (cat.MEP, "Lift", "Liftlərin quraşdırılması", "əd", 2, 150_000),
]
SITE_LINES: List[Tuple[str, str, str, float, float]] = [
    ("Ərazi abadlığı", "Yol və səki örtükləri", "m2", 14_000, 520_000),
    ("Xarici şəbəkələr", "Xarici su və kanalizasiya şəbəkələri", "m", 2_400, 380_000),
]

# Cumulative accepted share (0-1) by building and work type at the report date.
PROGRESS: Dict[str, Dict[str, float]] = {
    "Bina-1": {cat.FRAME: 0.97, cat.MASONRY: 0.35, cat.ENVELOPE: 0.02, cat.FINISHING: 0.0, cat.MEP: 0.01},
    "Bina-2": {cat.FRAME: 0.90, cat.MASONRY: 0.45, cat.ENVELOPE: 0.01, cat.FINISHING: 0.0, cat.MEP: 0.01},
    "Bina-3": {cat.FRAME: 0.45, cat.MASONRY: 0.0, cat.ENVELOPE: 0.0, cat.FINISHING: 0.0, cat.MEP: 0.0},
    "Bina-4": {cat.FRAME: 0.82, cat.MASONRY: 0.13, cat.ENVELOPE: 0.0, cat.FINISHING: 0.0, cat.MEP: 0.01},
    "Bina-5": {cat.FRAME: 0.97, cat.MASONRY: 0.19, cat.ENVELOPE: 0.0, cat.FINISHING: 0.0, cat.MEP: 0.01},
    "Bina-6": {cat.FRAME: 0.66, cat.MASONRY: 0.02, cat.ENVELOPE: 0.0, cat.FINISHING: 0.0, cat.MEP: 0.0},
}

# Monthly F-2 totals before VAT, share of the cumulative value (months without a certificate are absent).
F2_SHARES: List[Tuple[date, float]] = [
    (D(2025, 10, 31), 0.03), (D(2025, 12, 31), 0.17), (D(2026, 3, 31), 0.09), (D(2026, 4, 30), 0.12),
    (D(2026, 5, 31), 0.11), (D(2026, 6, 30), 0.10), (D(2026, 7, 31), 0.10), (D(2026, 8, 31), 0.10),
    (D(2026, 9, 30), 0.13), (D(2026, 10, 31), 0.05),
]

CONTRACT = ContractTerms(
    number="54-N", signed=SIGNED, client=CLIENT, contractor=CONTRACTOR, subject=NAME, start=START, finish=FINISH,
    duration_months=16, performance_guarantee_pct=5, advance_pct=30, advance_guarantee_months=10, payment_days=15,
    penalty_pct_per_day=0.1, penalty_cap_pct=10, warranty_months=24, source="sample",
)

EVENTS = [
    ("E1", "Bina-3 üzrə layihə dəyişikliyi (özül)", D(2026, 1, 10), D(2026, 2, 20), "B3-FR", "Layihə / dizayn", "Sifarişçi"),
    ("E2", "Qış şəraiti, beton işləri dayandırıldı", D(2026, 1, 5), D(2026, 2, 15), "B1-FR B2-FR B4-FR", "Hava şəraiti", "Neytral"),
    ("E3", "Hörgü briqadalarının çatışmazlığı", D(2026, 6, 1), D(2026, 9, 30), "B1-MA B2-MA B4-MA B5-MA", "İşçi qüvvəsi", "Podratçı"),
]


def _schedule() -> List[Activity]:
    acts: List[Activity] = []
    for index, building in enumerate(BUILDINGS):
        number = building.split("-")[1]
        frame_start = START + timedelta(days=12 + index * 20)
        plan = {
            cat.FRAME: (frame_start, 165),
            cat.MASONRY: (frame_start + timedelta(days=110), 125),
            cat.ENVELOPE: (frame_start + timedelta(days=170), 130),
            cat.FINISHING: (frame_start + timedelta(days=235), 120),
            cat.MEP: (frame_start + timedelta(days=205), 150),
        }
        names = {cat.FRAME: "Karkas (torpaq, özül, dəmir-beton)", cat.MASONRY: "Hörgü işləri", cat.ENVELOPE: "Dam, fasad, qapı-pəncərə",
                 cat.FINISHING: "Daxili bəzək işləri", cat.MEP: "Mühəndis sistemləri və lift"}
        codes = {cat.FRAME: "FR", cat.MASONRY: "MA", cat.ENVELOPE: "EN", cat.FINISHING: "FI", cat.MEP: "ME"}
        previous = None
        for category in (cat.FRAME, cat.MASONRY, cat.ENVELOPE, cat.FINISHING, cat.MEP):
            start, days = plan[category]
            share = PROGRESS[building][category]
            act_id = f"B{number}-{codes[category]}"
            acts.append(Activity(
                id=act_id, wbs=building, name=f"{building} — {names[category]}", planned_start=start,
                planned_finish=min(start + timedelta(days=days), FINISH - timedelta(days=14)), progress=round(share * 100, 1),
                actual_start=(start + timedelta(days=25)) if share > 0 else None,
                predecessors=[previous] if previous and category != cat.MEP else ([f"B{number}-EN"] if category == cat.MEP else []),
                source="sample"))
            previous = act_id
    acts.append(Activity(id="S-01", wbs="Ərazi", name="Ərazi abadlığı və xarici şəbəkələr", planned_start=D(2026, 5, 1),
                         planned_finish=D(2026, 12, 20), progress=0.0, source="sample"))
    return acts


def _cost_lines() -> List[CostLine]:
    lines: List[CostLine] = []
    for building in BUILDINGS:
        for category, section, name, unit, qty, value in LINES_PER_BUILDING:
            share = PROGRESS[building][category]
            cum_qty = qty * share
            cum_value = value * share
            if building == "Bina-3" and "Armatur" in name:
                cum_qty, cum_value = qty, value  # rebar certified in full, concrete not poured
            if building == "Bina-3" and "Beton" in name:
                cum_qty, cum_value = 0.0, 0.0
            lines.append(CostLine(name=name, unit=unit, building=building, section=section, category=category,
                                  estimate_qty=qty, estimate_value=value, cum_qty=round(cum_qty, 1), cum_value=round(cum_value, 2),
                                  period_qty=None, period_value=None, source="sample"))
    for section, name, unit, qty, value in SITE_LINES:
        lines.append(CostLine(name=name, unit=unit, building=None, section=section, category=cat.SITE, estimate_qty=qty,
                              estimate_value=value, cum_qty=0.0, cum_value=0.0, source="sample"))
    cum = sum(l.cum_value or 0 for l in lines)
    month_share = dict(F2_SHARES)[REPORT_DATE]
    for line in lines:
        line.period_value = round((line.cum_value or 0) * month_share, 2)
    assert cum > 0
    return lines


def _payments(cum: float) -> List[PaymentCertificate]:
    certs = []
    running = 0.0
    for number, (period, share) in enumerate(F2_SHARES, start=1):
        amount = round(cum * share, 2)
        running += amount
        certs.append(PaymentCertificate(source="sample", period=period, number=str(number), amount=amount,
                                        amount_with_vat=round(amount * (1 + VAT), 2), cumulative=round(running, 2)))
    return certs


def estate_sample_input() -> DelayInput:
    from .reader import _party, _split_ids

    lines = _cost_lines()
    estimate = sum(l.estimate_value for l in lines)
    cum = sum(l.cum_value or 0 for l in lines)
    contract_value = round(estimate * 1.02 * (1 + VAT), -3)
    terms = ContractTerms(**vars(CONTRACT))
    terms.value_with_vat = contract_value
    advance = round(contract_value * 0.30, 2)
    works_vat = round(cum * (1 + VAT), 2)
    withheld = round(works_vat * 0.30, 2)
    period_vat = round(cum * dict(F2_SHARES)[REPORT_DATE] * (1 + VAT), 2)
    f3 = F3Summary(source="sample", period=REPORT_DATE, number="10", works_cum=works_vat, works_period=period_vat,
                   advance_received=advance, advance_withheld_cum=withheld, advance_withheld_period=round(period_vat * 0.3, 2),
                   advance_remaining=round(advance - withheld, 2), payable_period=round(period_vat * 0.7, 2))
    project = ProjectInfo(name=NAME, client=CLIENT, contractor=CONTRACTOR, location="Nümunə şəhəri", contract_start=START,
                          contract_finish=FINISH, data_date=REPORT_DATE, currency="AZN", contract_value=contract_value)
    events = [DelayEvent(id=e[0], description=e[1], start=e[2], finish=e[3], activity_ids=_split_ids(e[4]), cause=e[5],
                         responsible=_party(e[6])) for e in EVENTS]
    return DelayInput(project=project, activities=_schedule(), events=events, payments=_payments(cum), contract=terms,
                      cost_lines=lines, f3=[f3], sources=["sample"])
