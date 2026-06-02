# DevBareun v1.3.1 — Stripe Payment + Credit Enforcement

## Completed

- Added `backend/app/saas_payments.py`.
- Added `backend/app/saas_credits.py`.
- Updated SaaS routes for one-time checkout, subscription checkout, webhook handling, pilot activation, and credit status.
- Added credit enforcement to `/api/analysis/create`.
- Added plan credit model:
  - Single Project = 1 credit
  - Plus = 5 monthly credits
  - Pro = 20 monthly credits
- Added environment variable documentation for Stripe.
- Updated backend version to `1.3.1-stripe-payment-credit-enforcement`.

## Important

This is a payment/credit foundation layer. If Stripe secrets are not configured, checkout endpoints create pilot records and return `mode: stripe_secret_missing`. With Stripe env variables configured, real Checkout Sessions are created.

Before commercial launch, protect or remove `/api/payments/activate-pilot-checkout`.
