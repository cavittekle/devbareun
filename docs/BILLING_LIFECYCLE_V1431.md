# Billing Lifecycle

## Current state: no online payment provider

Lemon Squeezy was removed from DevBareun. No online payment provider is connected, and the platform does not create checkouts or receive payment webhooks.

- `POST /api/billing/create-checkout`, `/create-subscription-checkout` and `/create-one-time-checkout` validate the plan, then return HTTP 503 with `error: payments_unavailable` and a message asking the customer to email info@devbareun.com.
- There is no payment webhook route. `/api/billing/webhook` and `/api/payments/webhook` were removed.
- Plan limits, subscriptions, analysis credits and usage counting are provider-agnostic and still work from existing database rows.
- `GET /api/billing/checkouts/{checkout_id}` still returns an owner-scoped summary of any existing checkout record. It does not expose provider URLs, customer emails or raw payloads.

## Activating a plan manually

Until a new provider is chosen, an owner or finance admin activates a plan by inserting the matching `subscriptions` or `analysis_credits` row in Supabase for the customer.

## Database

The v1.4.31 migration (`database/2026_06_21_v1431_billing_lifecycle_integrity.sql`) is already applied history and is not edited. Its webhook claim functions remain in the database but are not called by the backend.

## Adding a provider later

Add the provider's checkout and signed-webhook handling in `backend/app/services/billing_service.py`, keep provider logic separate from plan, credit and usage logic, and add its backend-only env vars to the Railway templates. Do not put payment secrets in Vercel.
