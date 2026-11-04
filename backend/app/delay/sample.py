"""Bundled example project and the Excel input template.

The sample is clearly an example (it feeds the public demo report); the
template generator writes ``frontend/templates/devbareun-delay-analysis-template.xlsx``.
Run ``python -m app.delay.sample`` from ``backend/`` to regenerate it.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, List, Sequence

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

PROJECT_ROWS = [
    ("Layihənin adı / Project name", "Baku Business Center (nümunə)", "Required"),
    ("Sifarişçi / Client", "Nümunə Sifarişçi MMC", ""),
    ("Podratçı / Contractor", "Nümunə Podratçı MMC", ""),
    ("Ünvan / Location", "Bakı", ""),
    ("Müqavilə başlanğıcı / Contract start", D(2023, 9, 1), "dd.mm.yyyy"),
    ("Müqavilə bitmə tarixi / Contract finish", D(2024, 12, 15), "Planned completion used for delay"),
    ("Hesabat tarixi / Data date", D(2024, 5, 31), "Status (cut-off) date of the actual progress"),
    ("Valyuta / Currency", "AZN", ""),
    ("Müqavilə dəyəri / Contract value", SAMPLE_CONTRACT_VALUE, "Compared with the F2 certified value"),
]

BASELINE_HEADERS = ["İş kodu / Activity ID", "Bölmə / WBS", "İşin adı / Activity Name", "Plan başlanğıc / Planned Start",
                    "Plan bitmə / Planned Finish", "Çəki / Weight", "Əvvəlki işlər / Predecessors"]
ACTUAL_HEADERS = ["İş kodu / Activity ID", "Faktiki başlanğıc / Actual Start", "Faktiki bitmə / Actual Finish",
                  "Proqnoz bitmə / Forecast Finish", "İcra % / Actual Progress %"]
EVENT_HEADERS = ["Hadisə ID / Event ID", "Hadisə / Delay Event", "Başlanğıc / Start", "Bitmə / Finish",
                 "Təsir etdiyi işlər / Affected Activities", "Səbəb / Cause", "Məsul tərəf / Responsible Party", "Qeyd / Notes"]
F2_HEADERS = ["Ay / Month", "F2 № / Certificate No", "Məbləğ ƏDV-siz / Amount excl. VAT", "Məbləğ ƏDV ilə / Amount incl. VAT"]
MONTHLY_HEADERS = ["Ay / Month", "Plan kumulyativ % / Planned Cumulative %", "Faktiki kumulyativ % / Actual Cumulative %"]

README_LINES = [
    "DevBareun — Tikinti layihəsinin icra və gecikmə analizi şablonu / Construction execution and delay analysis template",
    "",
    "1. Layihə / Project: layihə məlumatları və hesabat tarixi (data date).",
    "2. Plan_Qrafik / Baseline: hər iş üçün plan başlanğıc və bitmə. Çəki boşdursa, plan müddəti çəki kimi götürülür. Əvvəlki işləri boşluq və ya vergüllə yazın (məs. A100 A110).",
    "3. Faktiki_Icra / Actual: eyni iş kodları ilə faktiki tarixlər və icra faizi (0-100).",
    "4. Gecikme_Hadiseleri / Delay_Events (istəyə bağlı): gecikmə hadisələri, məsul tərəf = Sifarişçi / Podratçı / Neytral.",
    "5. Ayliq_Icra / Monthly (istəyə bağlı): aylıq kumulyativ plan və faktiki faiz. Boşdursa, işlərdən hesablanır.",
    "6. F2_Odenisler / F2 payments (istəyə bağlı): hər F2 aktı üçün ay və məbləğ. F2 fayllarını ayrıca da yükləyə bilərsiniz.",
    "",
    "Nümunə sətirləri silin və öz məlumatlarınızı daxil edin. Tarix formatı: dd.mm.yyyy və ya Excel tarixi.",
    "Delete the example rows and enter your own data. Dates: dd.mm.yyyy or Excel dates.",
    "Primavera XER və MS Project XML faylları da birbaşa yüklənə bilər / XER and MS Project XML exports can be uploaded directly.",
]


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

    _write_sheet(wb.create_sheet("Layihe_Project"), ["Sahə / Field", "Dəyər / Value", "Qeyd / Notes"], PROJECT_ROWS, [40, 34, 44])
    _write_sheet(wb.create_sheet("Plan_Qrafik_Baseline"), BASELINE_HEADERS,
                 [(a[0], a[1], a[2], a[3], a[4], a[5], a[6]) for a in SAMPLE_ACTIVITIES], [14, 26, 40, 16, 16, 10, 20])
    _write_sheet(wb.create_sheet("Faktiki_Icra_Actual"), ACTUAL_HEADERS,
                 [(a[0], a[7], a[8], None, a[9]) for a in SAMPLE_ACTIVITIES], [14, 18, 18, 18, 14])
    _write_sheet(wb.create_sheet("Gecikme_Hadiseleri_Events"), EVENT_HEADERS,
                 [(e[0], e[1], e[2], e[3], e[4], e[5], e[6], "") for e in SAMPLE_EVENTS], [12, 44, 14, 14, 20, 22, 18, 24])
    _write_sheet(wb.create_sheet("Ayliq_Icra_Monthly"), MONTHLY_HEADERS, [], [14, 24, 24])
    _write_sheet(wb.create_sheet("F2_Odenisler_Payments"), F2_HEADERS,
                 [(p[1], p[0], p[2], round(p[2] * 1.18, 2)) for p in SAMPLE_PAYMENTS], [14, 18, 26, 26])
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
