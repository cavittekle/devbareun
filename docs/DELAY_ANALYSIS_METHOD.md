# Execution and Delay Analysis Method

DevBareun produces one result: the construction execution and delay analysis
report (Tikinti layihəsinin icra və gecikmə analizi hesabatı). Code lives in
`backend/app/delay/` (`reader.py`, `documents.py`, `costs.py`, `categories.py`,
`engine.py`, `executive.py`, `report.py`, `report_a3.py`, `sample.py`,
`sample_estate.py`).

## Inputs

Uploads are grouped by document type:

| Type | Formats | What happens |
| --- | --- | --- |
| Contract (müqavilə) | PDF, Word, image | A terms table ("Xüsusi şərtlər") or the text of a Word / text-based PDF contract is searched for number, date, value, dates, advance %, advance guarantee months, payment days, penalty %/day and cap. Text matches are marked as "to be checked". Scanned PDFs and images are kept as references: enter the terms in the template's `Muqavile_Contract` sheet. |
| Planning (planlama) | Excel/CSV, Primavera XER, MS Project XML, `.mpp`, PDF | Excel/CSV/XER/XML are read as below; `.mpp` and PDF are kept as references (export to XML/Excel for the calculation). |
| F2 certificates | Excel/CSV, Word `.docx` (`.doc` kept as reference) | Reporting period, certificate number, total before VAT, total with VAT and value since the start of works. A register sheet with one row per period also works. In Excel the cumulative sheet ("Nakopitel", "Q.C", "smeta nakopitel") is read line by line: estimate value, cumulative and this-month value and quantities, by building and section. Rows without a unit are section or building headers; "Cəmi" and reserve rows are skipped. A Forma-3 sheet gives works with VAT, advance received / withheld / outstanding and the amount payable. |

F2 totals are summed per month and compared with physical progress:
financial progress = certified value / contract value. A gap above 10 points is
flagged (certified ahead: check measurements; behind: work not yet certified).
Duplicate months, missing months and F2s without a period are listed as data
quality notes.

Schedule files, one or more of:

| Format | What is read |
| --- | --- |
| `devbareun-delay-analysis-template.xlsx` | Project, baseline, actual progress, delay events, monthly progress |
| Any Excel/CSV plan-actual table | Sheets detected by column headers (EN / AZ / TR / RU) |
| Primavera P6 `.xer` | PROJECT, PROJWBS, TASK, TASKPRED |
| MS Project `.xml` | Baseline 0, actual dates, % complete, predecessor links |

Template sheets:

| Sheet | Required | Columns |
| --- | --- | --- |
| `Layihe_Project` | yes | project name, client, contractor, contract start/finish, data date, currency, contract value |
| `Muqavile_Contract` | no | contract number and date, value with VAT, VAT %, start, finish, advance %, advance guarantee months, payment days, penalty %/day, penalty cap % |
| `Plan_Qrafik_Baseline` | yes | activity ID, WBS/section, name, planned start, planned finish, weight, predecessors |
| `Faktiki_Icra_Actual` | yes | activity ID, actual start, actual finish, forecast finish, actual % |
| `Smeta_F2_Nakopitel` | no (recommended) | building, section, work item, unit, estimate qty and value, cumulative qty and value, this month's value (all before VAT, without the 2% reserve) |
| `F3_Forma3` | no | works with VAT, advance received, advance withheld, outstanding advance, amount payable |
| `Gecikme_Hadiseleri_Events` | no | event ID, description, start, finish, affected activities, cause, responsible party |
| `Ayliq_Icra_Monthly` | no | month, planned cumulative %, actual cumulative % |
| `F2_Odenisler_Payments` | no | month, F2 number, amount excl. VAT, amount incl. VAT |

The template's example rows are a fictional six-building estate
(`sample_estate.py`). Regenerate the template with
`cd backend && python -m app.delay.sample`.

## Calculations (calendar days)

1. **Planned progress** of an activity grows linearly from planned start to
   planned finish. Project progress = weight-averaged activity progress.
   Weight = the weight/value column, otherwise planned duration.
2. **SPI** = actual % / planned % at the data date.
3. **Schedule delay (earned schedule)**: the date on which the planned S-curve
   reached today's actual %. Delay = data date − that date.
4. **Activity forecast finish**, in order of preference: actual finish;
   supplied forecast; current production rate (from 20% progress; capped at
   3× planned duration); planned rate from the data date; planned duration
   from the data date for late starts.
5. **Network logic**: when at least a third of the activities have
   predecessors (finish-to-start), not-started work is pushed by late
   predecessors and a backward pass gives total float. Critical path =
   total float ≤ 0, including completed activities on the as-built driving
   path. Started successors are treated as out-of-sequence progress. Without
   logic, activities finishing within 7 days of the forecast completion are
   marked critical (approximate).
6. **Status**: completed, completed late, on track, not started, late start,
   delayed (≤ 14 days), major delay (> 14 days), critical delay (late and on
   the critical path).
7. **Forecast completion** = latest activity forecast finish. A second,
   independent forecast uses SPI(t) = earned schedule days / elapsed days.
8. **Delay events** are classified per calendar day: employer + contractor on
   the same day = concurrent; employer = excusable and compensable; neutral =
   excusable, not compensable; contractor = non-excusable. The "on critical
   path" column only counts events whose listed activities are critical (or
   that list no activities).
9. **Monthly development**: planned and actual cumulative % at each month end.
   Actual history is the supplied monthly sheet, otherwise reconstructed
   linearly from activity actual dates.
10. **Findings and recommendations** are rule-based, in EN and AZ, and only use
    numbers from the calculation.

## Execution report (estimate-weighted)

When estimate lines with F-2 values are present (`method = estimate_value`):

1. **Work types.** Each estimate line gets a work type from its section and
   name: earthworks/foundation/frame → reinforced concrete, walls → masonry,
   roof/facade/doors/windows → envelope, floors/finishes → finishing,
   MEP/lifts/furniture → MEP, landscaping/networks/pump station → site.
2. **Plan %.** The value of each (building, work type) is spread evenly over
   the baseline window of the schedule activities of the same building and
   work type. If that building has no such activity, the window of the same
   work type in other buildings is used and flagged. A work type planned to
   start before the one it depends on is flagged as an illogical schedule.
3. **Fact %** = cumulative F-2 / estimate, both before VAT and without the 2%
   reserve. It is certified value, not a physical measurement; the report
   says so.
4. **Delay** = report date − the date the plan curve reached the fact %
   (earned schedule).
5. **Forecast.** Earliest finish = report date + (baseline finish − earned
   schedule date). The last 3 months' F-2 pace gives a date only when it is
   under 36 months, otherwise "the pace is unacceptable". Required pace to
   meet the contract date is compared with the recent pace.
6. **Penalty**: %/day × days late, the cap, and the date the cap is reached
   (contract finish + cap ÷ %/day). The basis is marked for legal checking.
7. **Finance**: works with VAT (Forma-3, or F-2 × 1.18), advance received,
   withheld and outstanding; an advance is not work done. The advance
   guarantee end (signing date + months) is flagged when it falls within 90
   days of the report date while advance is outstanding. A missing payment
   register is reported as "not provided".
8. **Physical checks**: concrete m³, rebar t and masonry m² per building;
   rebar certified (≥ 50%) while concrete is ≤ 5% is flagged.
9. **Texts**: key message, 3 key delays, 3–5 delay cards (cause, impact, who),
   unconfirmed causes, forecast lines, finance notes, 5 contractor actions and
   5 director decisions, in AZ and EN, only with numbers from the documents.

Without estimate lines (`method = activity_weights`) the same report is built
from schedule activity weights: fact % comes from the schedule progress,
paces are given in % per month and no money values are shown for plan.

The PDF is two A3 landscape pages: page 1 has the header, key message, KPI
tiles, S-curve (plan dashed, fact solid), monthly plan vs F-2 bars, the
work-type table with the key delays and the buildings table; page 2 has the
delay cards, the forecast and penalty table, finance vs physical progress,
contractor actions and director decisions. The download name is
`<Project> icra hesabatı -<month>.<year>.pdf`. The Excel report adds work-type,
building, monthly plan vs F-2 and finance/forecast sheets.

## Output

`analyze()` returns `schema = "devbareun.delay-analysis/v1"` with `project`,
`kpis`, `activities`, `top_delays`, `critical_path`, `wbs`, `monthly`,
`events`, `findings`, `actions`, `data_quality`, `method` and `executive`
(`schema = "devbareun.execution-report/v2"`: `totals`, `monthly`, `forecast`,
`penalty`, `finance`, `physical`, `categories`, `buildings`, `texts`).
Saved analyses keep it under `analysis_results.dashboard_data.delay_analysis`.

## API

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/api/delay-analysis/template` | public |
| GET | `/api/delay-analysis/sample` | public (example data) |
| GET | `/api/delay-analysis/sample/report?format=pdf\|xlsx&lang=az\|en` | public (example data) |
| POST | `/api/delay-analysis/preview` (multipart `files`, ≤ 5 files, ≤ 15 MB each) | signed in |
| GET | `/api/delay-analysis/project/{project_id}` | project access |
| GET | `/api/delay-analysis/project/{project_id}/report?format=pdf\|xlsx&lang=az\|en` | project access |

Every analysis job (`POST /api/analysis/start/{project_id}`) also runs the
delay engine on the same checksum-verified, security-screened files.
