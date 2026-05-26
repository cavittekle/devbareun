# DevBareun v0.9.0 — Workforce & Productivity Planning

This release adds the missing Workforce & Productivity Planning module.

## Added

- `app/productivity.py`
- `app/libraries/activity_library.json`
- `app/libraries/labor_library.json`
- `app/libraries/equipment_library.json`
- `app/libraries/productivity_library.json`
- Required workforce calculation
- Realistic duration calculation
- Workforce gap analysis
- Activity delay risk scoring
- Productivity planning evidence in preflight and dashboard payload

## Core formulas

```text
required_workers = quantity / (productivity_per_worker_day × planned_days)
realistic_days = quantity / (actual_workers × productivity_per_worker_day)
```

## Guardrail

If activity type, quantity, unit, planned duration or actual workers are missing, DevBareun marks the row as `needs_confirmation` and does not invent workforce results.

Expected backend health version:

```text
0.9.0-workforce-productivity-planning
```
