# DevBareun v1.0.1 — Dynamic Schedule / Progress Result Dashboard

This release adds a construction-specific dynamic result dashboard for plan-vs-actual schedule/progress analysis.

## Added

- Dynamic Schedule / Progress dashboard renderer
- D-3 style project-control layout adapted for DevBareun result page
- Plan vs actual KPI cards
- Timeline progress bar
- Plan/actual trend bars
- Building / block / activity cards
- Detailed plan-vs-actual comparison table
- Risk pressure panel
- Recommended recovery actions section
- A3/PDF-friendly print styling
- Dark/light readability support

## Files

- `css/result-schedule-progress.css`
- `js/result-schedule-progress.js`
- `result-dashboard.html` updated to load the new CSS/JS
- `js/result-dynamic.js` updated to route schedule/progress/full dashboard results to the new renderer

## Principle

The dashboard is dynamic. It does not use fixed D-3 values. It reads backend dashboard JSON and shows placeholders only when confirmed data is not available.
