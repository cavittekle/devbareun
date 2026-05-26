# DevBareun v0.9.1 QA Hardening Summary

Tested locally with FastAPI TestClient and the Şəmkir cost-estimate Excel.

Fixed in this package:
- JS-off/slow-connection fallback text added to navigation and key i18n elements.
- FAQ wording changed from future/planned language to active commercial model wording.
- BACKEND_CONNECTION.md expected version updated to `0.9.1-qa-payment-ready`.
- Backend health version updated to `0.9.1-qa-payment-ready`.
- Mock payment gate added: dashboard analysis/export requires the pilot payment unlock endpoint before generation/download.
- Workforce template replaced with activity/quantity/duration/actual-workers fields for productivity analysis.

Payment note: Stripe is still not real; this is a pilot/mock payment gate. Real commercial launch still needs Stripe Checkout + webhook validation.
