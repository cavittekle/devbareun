# DevBareun v1.1.9 — Cost & F-2 Final Polish

## Purpose
This release finalizes the **Cost & Payment Control** package for Cost Estimate + F-2 review.

## Fixed
- Added `remaining_cost` to backend KPI payload.
- Added `cost_variance_amount` to backend KPI payload.
- Remaining value now uses: `Cost Estimate / Smeta baseline - Actual confirmed F-2`.
- Cost table now receives explicit `planned`, `actual`, `remaining`, and `variance` fields instead of inferred generic metric rows.
- Cost-specific executive summary avoids unnecessary schedule/workforce language.
- Result dashboard cost table formatting improved for money and variance fields.
- Added Azerbaijani translations for Cost & F-2 final dashboard wording.
- Backend version updated to `1.1.9-cost-f2-polish`.

## Expected Cost & Payment Control Output
For a smeta baseline of `3,139,625.02 AZN` and confirmed F-2 value of `3,109,800.02 AZN`, the dashboard should display:

- Cost Estimate / Smeta: `3,139,625.02 AZN`
- Actual confirmed F-2: `3,109,800.02 AZN`
- Remaining value: `29,825.00 AZN`
- Cost variance: about `-0.95%`

## Changed files
- `backend/app/analyzer.py`
- `backend/app/version.py`
- `frontend/js/result-analysis-specific.js`
- `frontend/js/az-glossary.js`
- `AGENTOPS_RELEASE_MANIFEST.json`
