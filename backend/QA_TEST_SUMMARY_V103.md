# DevBareun v1.0.3 QA Test Summary

Local QA completed for backend API, payment gate, reports and selected real files.

## Tested
- Backend Python compile: OK
- Health endpoint: OK
- Cost upload/preflight/analyze flow: OK
- Payment gate before analyze: OK, returns 402 until mock pilot payment
- Mock pilot payment unlock: OK
- PDF export EN/AZ: OK
- Excel export EN/AZ: OK
- Workforce productivity calculation: OK
- Workforce-only dashboard no longer displays unrelated cost/progress KPIs

## Real file tested
- Şəmkir Tikinti ASC FORMA2 - nokapitel.xlsx
  - Smeta detected: 2,452,691.30 AZN
  - Actual cost not confirmed: correctly shown as Not available / missing actual data
  - Payment required before analysis: OK
  - Exports after payment: OK

## Workforce template tested
- DevBareun Professional Upload Template v2.xlsx
  - Activities checked: 17
  - Calculated productivity activities: 4
  - Required workforce: 23
  - Actual workforce: 16
  - Workforce gap: -7
  - Max delay risk: 8.7 days

## Remaining commercial work
- Replace mock pilot payment with real Stripe Checkout + webhook
- Add user account / project history
- Continue parser tests with more real construction files
