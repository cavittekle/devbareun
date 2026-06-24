# v1.4.31 — Billing Lifecycle Integrity

## Scope

This release makes Lemon Squeezy checkout handling replay-safe and observable without storing raw provider payloads in the application database. It does not create invoices, change product prices or call the Lemon Squeezy API beyond the existing checkout creation request.

## Checkout lifecycle

Each new checkout now has a DevBareun-generated `checkout_id`. The backend persists a `checkout_sessions` record, sends that ID in Lemon Squeezy custom metadata and appends it to the verified success/cancel return URL. The customer workspace reads only:

```text
GET /api/billing/checkouts/{checkout_id}
```

The response excludes provider checkout URLs, customer emails, raw webhook payloads and payment-event metadata. It is owner-scoped; finance/owner staff can use it through the payment capability.

## Payment webhook state machine

`claim_payment_webhook_event` atomically claims a verified event. A duplicate is ignored only after `processing_status=processed`. A failed attempt remains retryable until `DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS`; then it becomes `dead_lettered`. `complete_payment_webhook_event` marks success only after subscription/credit side effects complete.

The persisted payload is a privacy-safe summary and SHA-256 fingerprint. Do not store raw provider payloads, tokens or customer email in `payment_events`.

## Subscription periods and credits

Subscription period end dates use provider `renews_at`, `ends_at` or trial fields where present. `used_project_count` resets only when the provider period advances. One-time credits are keyed by the provider event ID and are therefore idempotent under delivery retries. A refund revokes only an unused credit; a used credit becomes `refund_review_required` for manual finance review.

## Production configuration

Set the same bounded retry policy on Railway web, analysis worker and audit archive worker:

```env
DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS=5
```

Allowed range: `1–20`. Production webhooks must continue to use `LEMON_SQUEEZY_WEBHOOK_SECRET`. Do not put payment secrets in Vercel.

## Deployment

1. Apply `database/2026_06_21_v1431_billing_lifecycle_integrity.sql` after v1.4.30.
2. Set the retry env on all Railway services.
3. Deploy the web backend before testing checkout status polling.
4. Perform a real Lemon Squeezy test purchase and confirm: checkout record, pending status, webhook processing, entitlement grant and duplicate webhook no-op.
5. Test a provider retry by replaying the same signed event in the provider test environment; it must not issue an extra credit.

