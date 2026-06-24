# DevBareun v1.4.7 Result Dashboard UX

This release turns the React result viewer from a raw JSON payload screen into a management dashboard that can read both canonical executive dashboard responses and saved analysis result rows.

## Updated file

- `frontend/member-dashboard-app/src/pages/ResultViewer.jsx`
- `frontend/member-dashboard-app/src/styles.css`

## What changed

- Added an executive summary hero section.
- Added KPI cards for budget, actual cost, forecast cost and risk score.
- Added schedule/progress bars for planned progress and actual progress.
- Added variance and delay impact fields.
- Added a data quality panel with confidence, uploaded-file count, detected sheet count and warnings.
- Added a risk register panel that supports both executive dashboard `top_risks` and analyzer `risk_register` shapes.
- Added recommended actions rendering.
- Kept raw JSON available behind a manual “Show JSON” toggle for audit/debug use.

## Supported payload shapes

The view now normalizes the following response families:

- `/api/dashboard/executive/{project_id}`
- `/api/analysis/results/{project_id}` style `analysis_result` payloads
- `/api/guest-result/{token}` style `analysis_results` lists
- analyzer `dashboard_data.dashboard` payloads
- analytics-service `dashboard_data.metrics` payloads

## Product rule

Empty or unavailable fields remain visibly empty as `—`. The UI does not fabricate missing actual cost, progress, delay or risk values.
