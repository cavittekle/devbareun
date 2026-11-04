"""Bundled example project and the Excel input template.

The sample is clearly an example (it feeds the public demo report); the
template generator writes ``frontend/templates/devbareun-delay-analysis-template.xlsx``.
Run ``python -m app.delay.sample`` from ``backend/`` to regenerate it.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .model import Activity, DelayEvent, DelayInput, PaymentCertificate, ProjectInfo

D = date

# id, wbs, name, planned start, planned finish, weight, predecessors, actual start, actual finish, progress
SAMPLE_ACTIVITIES: List[tuple] = [
    ("A100", "1. Hazırlıq işləri", "Tikinti meydançasının hazırlanması", D(2023, 9, 1), D(2023, 9, 20), 2, "", D(2023, 9, 1), D(2023, 9, 22), 100),
    ("A110", "1. Hazırlıq işləri", "Qazıntı işləri", D(2023, 9, 21), D(2023, 10, 20), 4, "A100", D(2023, 9, 25), D(2023, 10, 31), 100),
    ("A200", "2. Özül", "Svay işləri", D(2023, 10, 21), D(2023, 11, 30), 6, "A110", D(2023, 11, 1), D(2023, 12, 18), 100),
    ("A210", "2. Özül", "Özül plitəsinin betonlanması", D(2023, 12, 1), D(2023, 12, 31), 6, "A200", D(2023, 12, 19), D(2024, 1, 29), 100),
    ("A300", "3. Karkas", "Zirzəmi divarları və örtüyü", D(2024, 1, 1), D(2024, 1, 31), 7, "A210", D(2024, 1, 30), D(2024, 3, 6), 100),
    ("A310", "3. Karkas", "1-5-ci mərtəbə karkası", D(2024, 2, 1), D(2024, 3, 31), 12, "A300", D(2024, 3, 7), None, 70),
    ("A320", "3. Karkas", "6-10-cu mərtəbə karkası", D(2024, 4, 1), D(2024, 5, 31), 12, "A310", None, None, 0),
    ("A330", "3. Karkas", "Dam örtüyü", D(2024, 6, 1), D(2024, 6, 30), 4, "A320", None, None, 0),
    ("A400", "4. Fasad və hörgü", "Divar hörgüsü 1-5", D(2024, 3, 15), D(2024, 5, 15), 6, "A310", D(2024, 4, 20), None, 30),
    ("A410", "4. Fasad və hörgü", "Divar hörgüsü 6-10", D(2024, 6, 1), D(2024, 7, 31), 6, "A320 A400", None, None, 0),
    ("A420", "4. Fasad və hörgü", "Fasad sistemi", D(2024, 7, 1), D(2024, 9, 30), 9, "A410", None, None, 0),
    ("A500", "5. Mühəndis sistemləri", "Elektrik təchizatı", D(2024, 4, 1), D(2024, 8, 31), 6, "A310", D(2024, 4, 15), None, 15),
    ("A510", "5. Mühəndis sistemləri", "Su və kanalizasiya", D(2024, 4, 1), D(2024, 8, 31), 5, "A310", D(2024, 4, 22), None, 12),
    ("A520", "5. Mühəndis sistemləri", "İstilik və havalandırma", D(2024, 6, 1), D(2024, 9, 30), 6, "A320", None, None, 0),
    ("A600", "6. Daxili bəzək", "Daxili bəzək işləri", D(2024, 8, 1), D(2024, 11, 15), 10, "A410 A500 A510", None, None, 0),
    ("A700", "7. Təhvil", "Sınaq və istismara vermə", D(2024, 11, 16), D(2024, 12, 15), 3, "A600 A520 A420", None, None, 0),
]

SAMPLE_EVENTS: List[tuple] = [
    ("E1", "Layihə sənədlərinin (svay) gec təsdiqi", D(2023, 10, 21), D(2023, 10, 31), "A200", "Layihə / dizayn", "Sifarişçi"),
    ("E2", "Güclü yağış, qazıntı dayandırıldı", D(2023, 10, 14), D(2023, 10, 20), "A110", "Hava şəraiti", "Neytral"),
    ("E3", "Beton zavodunun tədarük gecikməsi", D(2024, 1, 8), D(2024, 1, 26), "A210", "Material tədarükü", "Podratçı"),
    ("E4", "Armatur dəyişikliyi (variasiya əmri)", D(2024, 1, 15), D(2024, 1, 29), "A210 A300", "Dəyişiklik əmri", "Sifarişçi"),
    ("E5", "Karkas briqadasının çatışmazlığı", D(2024, 3, 10), D(2024, 4, 30), "A310", "İşçi qüvvəsi", "Podratçı"),
]


SAMPLE_CONTRACT_VALUE = 18_500_000.0

# F2 certificate number, period end, amount before VAT (AZN)
SAMPLE_PAYMENTS: List[tuple] = [
    ("F2-01", D(2023, 9, 30), 320_000.0),
    ("F2-02", D(2023, 10, 31), 550_000.0),
    ("F2-03", D(2023, 11, 30), 780_000.0),
    ("F2-04", D(2023, 12, 31), 950_000.0),
    ("F2-05", D(2024, 1, 31), 1_020_000.0),
    ("F2-06", D(2024, 2, 29), 880_000.0),
    ("F2-07", D(2024, 3, 31), 860_000.0),
    ("F2-08", D(2024, 4, 30), 820_000.0),
    ("F2-09", D(2024, 5, 31), 800_000.0),
]


def sample_input() -> DelayInput:
    from .reader import _party, _split_ids  # local import avoids a cycle at module load

    activities = [
        Activity(id=a[0], wbs=a[1], name=a[2], planned_start=a[3], planned_finish=a[4], weight=float(a[5]),
                 predecessors=_split_ids(a[6]), actual_start=a[7], actual_finish=a[8], progress=float(a[9]),
                 source="sample")
        for a in SAMPLE_ACTIVITIES
    ]
    events = [
        DelayEvent(id=e[0], description=e[1], start=e[2], finish=e[3], activity_ids=_split_ids(e[4]), cause=e[5],
                   responsible=_party(e[6]))
        for e in SAMPLE_EVENTS
    ]
    project = ProjectInfo(name="Baku Business Center (nümunə)", client="Nümunə Sifarişçi MMC", contractor="Nümunə Podratçı MMC",
                          location="Bakı", contract_start=D(2023, 9, 1), contract_finish=D(2024, 12, 15),
                          data_date=D(2024, 5, 31), currency="AZN", contract_value=SAMPLE_CONTRACT_VALUE)
    payments = [PaymentCertificate(source="sample", number=p[0], period=p[1], amount=p[2], amount_with_vat=round(p[2] * 1.18, 2))
                for p in SAMPLE_PAYMENTS]
    return DelayInput(project=project, activities=activities, events=events, payments=payments, sources=["sample"])


# ------------------------------------------------------------------ template
TEMPLATE_FILENAME = "devbareun-delay-analysis-template.xlsx"

BASELINE_HEADERS = ["İş kodu / Activity ID", "Bölmə / WBS", "İşin adı / Activity Name", "Plan başlanğıc / Planned Start",
                    "Plan bitmə / Planned Finish", "Çəki / Weight", "Əvvəlki işlər / Predecessors"]
ACTUAL_HEADERS = ["İş kodu / Activity ID", "Faktiki başlanğıc / Actual Start", "Faktiki bitmə / Actual Finish",
                  "Proqnoz bitmə / Forecast Finish", "İcra % / Actual Progress %"]
EVENT_HEADERS = ["Hadisə ID / Event ID", "Hadisə / Delay Event", "Başlanğıc / Start", "Bitmə / Finish",
                 "Təsir etdiyi işlər / Affected Activities", "Səbəb / Cause", "Məsul tərəf / Responsible Party", "Qeyd / Notes"]
F2_HEADERS = ["Ay / Month", "F2 № / Certificate No", "Məbləğ ƏDV-siz / Amount excl. VAT", "Məbləğ ƏDV ilə / Amount incl. VAT"]
MONTHLY_HEADERS = ["Ay / Month", "Plan kumulyativ % / Planned Cumulative %", "Faktiki kumulyativ % / Actual Cumulative %"]
COST_HEADERS = ["Bina / Building", "Bölmə / Section", "İşin adı / Work item", "Ölçü vahidi / Unit", "Smeta həcmi / Estimate qty",
                "Smeta dəyəri ƏDV-siz / Estimate value excl. VAT", "Kumulyativ həcm / Cumulative qty",
                "Kumulyativ dəyər ƏDV-siz / Cumulative value excl. VAT", "Hesabat ayı dəyəri / This month value"]

README_LINES = [
    "DevBareun — Tikinti layihəsinin icra və gecikmə analizi şablonu / Construction execution and delay analysis template",
    "",
    "1. Layihe_Project: layihə məlumatları və hesabat tarixi (data date).",
    "2. Muqavile_Contract: müqavilənin əsas şərtləri (məbləğ, müddət, avans, avans təminatı, cərimə və limiti). Skan müqavilə oxunmur — şərtləri burada yazın.",
    "3. Plan_Qrafik_Baseline: hər iş üçün plan başlanğıc və bitmə. İş adını bina və iş növü ilə yazın (məs. 'Bina-1 — Hörgü işləri'). Əvvəlki işləri boşluq və ya vergüllə yazın.",
    "4. Faktiki_Icra_Actual: eyni iş kodları ilə faktiki tarixlər və icra faizi (0-100).",
    "5. Smeta_F2_Nakopitel: smeta sətirləri və kumulyativ F-2 (ƏDV-siz, 2% ehtiyatsız). Fakt % = kumulyativ F-2 / smeta. 'Cəmi' sətirləri yazmayın.",
    "6. F3_Forma3 (istəyə bağlı): Forma-3 üzrə görülmüş iş, avans, tutulmuş və qalıq avans.",
    "7. F2_Odenisler_Payments (istəyə bağlı): hər ayın F-2 aktı (ay və məbləğ) — aylıq qrafik və son 3 ayın tempi üçün.",
    "8. Gecikme_Hadiseleri_Events və Ayliq_Icra_Monthly (istəyə bağlı).",
    "",
    "Nümunə uydurma layihədir: sətirləri silin və öz məlumatlarınızı daxil edin. Tarix formatı: dd.mm.yyyy və ya Excel tarixi.",
    "The example is a fictional project: delete its rows and enter your own data. Dates: dd.mm.yyyy or Excel dates.",
    "Primavera XER və MS Project XML faylları da birbaşa yüklənə bilər / XER and MS Project XML exports can be uploaded directly.",
]


def _template_data() -> Dict[str, List[Sequence[Any]]]:
    from .sample_estate import EVENTS, estate_sample_input

    inp = estate_sample_input()
    info, terms = inp.project, inp.contract
    project_rows = [
        ("Layihənin adı / Project name", info.name, "Required"),
        ("Sifarişçi / Client", info.client, ""),
        ("Podratçı / Contractor", info.contractor, ""),
        ("Ünvan / Location", info.location, ""),
        ("Müqavilə başlanğıcı / Contract start", info.contract_start, "dd.mm.yyyy"),
        ("Müqavilə bitmə tarixi / Contract finish", info.contract_finish, "Planned completion used for delay"),
        ("Hesabat tarixi / Data date", info.data_date, "Status (cut-off) date, usually the F-2 month end"),
        ("Valyuta / Currency", info.currency, ""),
        ("Müqavilə dəyəri / Contract value", info.contract_value, "ƏDV ilə / incl. VAT"),
    ]
    contract_rows = [
        ("Müqavilə nömrəsi / Contract No", terms.number, ""),
        ("Müqavilə tarixi / Contract date", terms.signed, "dd.mm.yyyy"),
        ("Sifarişçi / Client", terms.client, ""),
        ("Podratçı / Contractor", terms.contractor, ""),
        ("Müqavilə məbləği ƏDV ilə / Contract value incl. VAT", terms.value_with_vat, "AZN"),
        ("ƏDV dərəcəsi % / VAT rate %", 18, ""),
        ("Başlama tarixi / Start date", terms.start, ""),
        ("Bitmə tarixi / Completion date", terms.finish, ""),
        ("Müddət, ay / Duration, months", terms.duration_months, ""),
        ("İcra təminatı % / Performance guarantee %", terms.performance_guarantee_pct, ""),
        ("Avans faizi % / Advance %", terms.advance_pct, ""),
        ("Avans təminatı müddəti, ay / Advance guarantee, months", terms.advance_guarantee_months, "müqavilə tarixindən / from signing"),
        ("Ödəniş müddəti, gün / Payment term, days", terms.payment_days, ""),
        ("Gündəlik cərimə % / Penalty per day %", terms.penalty_pct_per_day, "müqavilə dəyərindən / of the contract value"),
        ("Cərimə limiti % / Penalty cap %", terms.penalty_cap_pct, ""),
        ("Zəmanət müddəti, ay / Warranty, months", terms.warranty_months, ""),
    ]
    baseline = [(a.id, a.wbs, a.name, a.planned_start, a.planned_finish, a.weight, " ".join(a.predecessors)) for a in inp.activities]
    actual = [(a.id, a.actual_start, a.actual_finish, None, a.progress) for a in inp.activities]
    events = [(e[0], e[1], e[2], e[3], e[4], e[5], e[6], "") for e in EVENTS]
    payments = [(c.period, c.number, c.amount, c.amount_with_vat) for c in inp.payments]
    costs = [(l.building or "", l.section, l.name, l.unit, l.estimate_qty, l.estimate_value, l.cum_qty, l.cum_value, l.period_value)
             for l in inp.cost_lines]
    f3 = inp.f3[0]
    f3_rows = [
        (f"Forma-3 № {f3.number} — hesabat dövrü / period {f3.period.strftime('%d.%m.%Y')}", None, None),
        ("Göstərici / Item", "Kumulyativ / Cumulative", "Hesabat ayı / This month"),
        ("Görülmüş işlərin dəyəri ƏDV ilə / Works done incl. VAT", f3.works_cum, f3.works_period),
        ("Alınmış avans / Advance received", f3.advance_received, None),
        ("Avansdan tutulmuş / Advance withheld", f3.advance_withheld_cum, f3.advance_withheld_period),
        ("Qalıq avans / Remaining advance", f3.advance_remaining, None),
        ("Ödəniləcək məbləğ / Amount payable", None, f3.payable_period),
    ]
    return {"project": project_rows, "contract": contract_rows, "baseline": baseline, "actual": actual, "events": events,
            "payments": payments, "costs": costs, "f3": f3_rows}


def _write_sheet(ws: Any, headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[int]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    fill = PatternFill("solid", fgColor="0B1730")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="E3B256")
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=index).column_letter].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, date):
                cell.number_format = "DD.MM.YYYY"


def build_template_bytes() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    readme = wb.active
    readme.title = "README"
    for line in README_LINES:
        readme.append([line])
    readme.column_dimensions["A"].width = 140

    data = _template_data()
    _write_sheet(wb.create_sheet("Layihe_Project"), ["Sahə / Field", "Dəyər / Value", "Qeyd / Notes"], data["project"], [40, 44, 44])
    _write_sheet(wb.create_sheet("Muqavile_Contract"), ["Şərt / Term", "Dəyər / Value", "Qeyd / Notes"], data["contract"], [52, 26, 36])
    _write_sheet(wb.create_sheet("Plan_Qrafik_Baseline"), BASELINE_HEADERS, data["baseline"], [12, 14, 44, 16, 16, 10, 20])
    _write_sheet(wb.create_sheet("Faktiki_Icra_Actual"), ACTUAL_HEADERS, data["actual"], [12, 18, 18, 18, 14])
    _write_sheet(wb.create_sheet("Smeta_F2_Nakopitel"), COST_HEADERS, data["costs"], [10, 22, 40, 10, 14, 20, 16, 22, 18])
    _write_sheet(wb.create_sheet("F3_Forma3"), list(data["f3"][0]), data["f3"][1:], [56, 20, 20])
    _write_sheet(wb.create_sheet("F2_Odenisler_Payments"), F2_HEADERS, data["payments"], [14, 18, 26, 26])
    _write_sheet(wb.create_sheet("Gecikme_Hadiseleri_Events"), EVENT_HEADERS, data["events"], [12, 44, 14, 14, 24, 22, 18, 24])
    _write_sheet(wb.create_sheet("Ayliq_Icra_Monthly"), MONTHLY_HEADERS, [], [14, 24, 24])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def write_template(target: Path) -> Path:
    target.write_bytes(build_template_bytes())
    return target


if __name__ == "__main__":  # pragma: no cover - maintenance helper
    root = Path(__file__).resolve().parents[3]
    out = write_template(root / "frontend" / "templates" / TEMPLATE_FILENAME)
    print(f"Wrote {out}")
