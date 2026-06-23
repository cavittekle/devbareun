
# DevBareun v1.3.6 — Persistent Analysis + Saved Dashboards

## Purpose
Turns generated dashboards into saved workspace records.

## New backend routes
- `POST /api/workspace/projects`
- `GET /api/workspace/projects`
- `POST /api/workspace/analysis/save`
- `GET /api/workspace/analysis`
- `GET /api/workspace/analysis/{analysis_id}`
- `POST /api/workspace/guest-results`
- `GET /api/workspace/guest-results/{token}`

## Supabase
Run:

```sql
database/2026_05_27_v136_persistent_analysis.sql
```

## Frontend
React workspace views:
- `/workspace/?view=result`
- `/workspace/?view=guest-result`

Updated:
- `/workspace/?view=projects`
- `/workspace/?view=reports`
