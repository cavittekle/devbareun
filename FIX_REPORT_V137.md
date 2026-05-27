# DevBareun v1.3.7 — Report Archive + A4/A3 Print System

## Added

- Report Archive UI in `frontend/reports.html` with search, package filter, status metadata and action buttons.
- Saved report detail page in `frontend/analysis-view.html` with print-ready report layout.
- A4/A3 browser print controller in `frontend/js/report-print-system.js`.
- Print styling layer in `frontend/css/report-print.css`.
- Backend report archive endpoints under `/api/workspace/reports`.
- Automatic report archive row creation whenever `/api/workspace/analysis/save` is used.
- Optional A3 PDF export via `/api/projects/{project_id}/report/pdf?paper=a3`.
- Supabase migration: `database/2026_05_27_v137_report_archive_print.sql`.

## Print behavior

- A4 = portrait formal report output.
- A3 = landscape wide dashboard/report output.
- Print size is stored in `localStorage` as `devbareun_print_size`.
- Direct archive links support `analysis-view.html?id=...&print=A3&auto=print`.

## Deployment note

Apply the v1.3.7 SQL migration before relying on Supabase-backed report archive persistence. If migration is not applied, saved dashboards still work and the backend does not block analysis saving.
