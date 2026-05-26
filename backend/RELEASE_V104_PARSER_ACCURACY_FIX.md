# DevBareun Backend v1.0.4 Parser Accuracy Fix

## Fixed
- Prevented KPI/value rows from being treated as table headers during generic Excel parsing.
- Prevented negative or non-cost numeric values from becoming total cost.
- Added English smeta/BOQ total labels such as `Smeta total`, `Estimate total`, `Contract total`, and `Grand total`.
- Improved F-2 / progress payment reading: `This Period Amount` columns are summed, while cumulative-style columns remain protected by validation.
- Cost-only analysis no longer adds workforce productivity warnings from unrelated sheets.
- Negative delay values are normalized to 0 and kept in evidence for auditability.

## QA result
- Backend compile: PASS
- Health endpoint: PASS
- Upload / preflight / payment gate / analyze: PASS
- PDF export EN/AZ: PASS
- Excel export EN/AZ: PASS
- Frontend static checks: PASS

## Template test result
- Smeta total: 194,350 AZN
- F-2 completed amount: 98,150 AZN
- Actual execution: 50.5%
