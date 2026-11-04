# Execution and Delay Analysis Method

DevBareun produces one result: the construction execution and delay analysis
report (Tikinti layihəsinin icra və gecikmə analizi hesabatı). Code lives in
`backend/app/delay/` (`reader.py`, `engine.py`, `report.py`, `sample.py`).

## Inputs

Uploads are grouped by document type:

| Type | Formats | What happens |
| --- | --- | --- |
| Contract (müqavilə) | PDF, Word, image | Kept with the analysis and listed in the report. Contract dates and value come from the template's project sheet. |
| Planning (planlama) | Excel/CSV, Primavera XER, MS Project XML, `.mpp`, PDF | Excel/CSV/XER/XML are read as below; `.mpp` and PDF are kept as references (export to XML/Excel for the calculation). |
| F2 certificates | Excel/CSV, Word `.docx` (`.doc` kept as reference) | Reporting period, certificate number, total before VAT, total with VAT and value since the start of works. A register sheet with one row per period also works. |

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
| `Plan_Qrafik_Baseline` | yes | activity ID, WBS/section, name, planned start, planned finish, weight, predecessors |
| `Faktiki_Icra_Actual` | yes | activity ID, actual start, actual finish, forecast finish, actual % |
| `Gecikme_Hadiseleri_Events` | no | event ID, description, start, finish, affected activities, cause, responsible party |
| `Ayliq_Icra_Monthly` | no | month, planned cumulative %, actual cumulative % |
| `F2_Odenisler_Payments` | no | month, F2 number, amount excl. VAT, amount incl. VAT |

Regenerate the template with `cd backend && python -m app.delay.sample`.

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

## Output

`analyze()` returns `schema = "devbareun.delay-analysis/v1"` with `project`,
`kpis`, `activities`, `top_delays`, `critical_path`, `wbs`, `monthly`,
`events`, `findings`, `actions`, `data_quality`, `method`.
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
