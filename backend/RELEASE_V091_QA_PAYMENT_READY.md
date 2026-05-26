# DevBareun v0.9.1 — QA + Payment-Ready Pilot Hardening

This release was tested locally with FastAPI TestClient and the Şəmkir cost-estimate Excel.

## Fixed

- Added default HTML fallback text to navigation and key i18n elements for SEO, slow connections and JS-blocked scenarios.
- Updated FAQ wording from future/planned wording to active commercial wording.
- Updated BACKEND_CONNECTION expected backend version to `0.9.1-qa-payment-ready`.
- Backend `/health` now returns `0.9.1-qa-payment-ready`.
- Added pilot/mock payment gate before dashboard generation and PDF/Excel export.
- Rebuilt workforce template to match workforce productivity calculations: activity, unit, quantity, planned duration and actual workers.
- Removed irrelevant cost warning from workforce-only productivity analysis.

## Payment note

Stripe is still not live in this release. The current payment endpoint is pilot/mock mode. Before commercial launch, implement Stripe Checkout + webhook validation.
