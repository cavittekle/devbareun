# DevBareun v0.8.3 — Baseline/Actual Upload Requirements UI

This release adds a clearer customer upload flow for each analysis type.

## Product rule

No actual data → no comparison result.  
Unclear actual data → needs confirmation.  
Confirmed actual data → calculate dashboard.

## Frontend changes

- Added a dynamic **Required data logic** panel below the analysis type selector.
- Cost Analysis now explains that full comparison requires Cost Estimate/Smeta + F-2/actual cost.
- Schedule / Delay now explains that delay comparison requires baseline schedule + actual progress.
- Progress Payment / F-2 now explains that actual execution requires completed amount linked to smeta/contract baseline.
- Workforce now explains that workforce gap requires required manpower + actual manpower.
- EN/AZ localization added for all new upload requirement texts.
- Light-mode readability is preserved for the new cards.

## Backend

Backend remains aligned with `0.8.1-baseline-actual-logic`.
