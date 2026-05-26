# DevBareun v0.6.3 — Downloadable Report Language Selection

This version adds language selection for downloadable dashboard reports.

## Frontend
- Result dashboard now includes a `Report language` selector.
- PDF and Excel export buttons pass `?lang=en` or `?lang=az` to the backend.
- Export language can follow the selected UI language or be changed separately.

## Backend
- `/api/projects/{project_id}/report/pdf?lang=en|az`
- `/api/projects/{project_id}/report/excel?lang=en|az`
- PDF and Excel labels, section headings, KPI labels, data quality labels and sheet profile labels are localized.
- `/health` version: `0.6.3-download-report-language`.

## Notes
The report data itself remains the uploaded/generated project data. Static dashboard/report labels are localized.
