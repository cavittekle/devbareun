# Billing Lifecycle

## Payment provider: Polar (polar.sh)

DevBareun sells its plans through Polar, organisation `devbareun`. Prices are in USD and match the public pricing section.

| Plan | Polar product | Price | Credits |
| --- | --- | --- | --- |
| Single Project | Single Project | $29 one-time | 1 project |
| Plus monthly | Plus (monthly) | $49 / month | 5 per month |
| Plus annual | Plus (annual) | $468 / year ($39 / month) | 60 per year |
| Pro monthly | Pro (monthly) | $89 / month | 20 per month |
| Pro annual | Pro (annual) | $852 / year ($71 / month) | 240 per year |

Each product and its Polar checkout link carry metadata `devbareun_plan` (`single`, `plus`, `pro`) and `billing_cycle` (`one_time`, `monthly`, `annual`). The webhook reads the plan from that metadata.

## Checkout flow

1. The workspace calls `POST /api/billing/create-one-time-checkout` or `/create-subscription-checkout` with `plan_code` and, for Plus and Pro, `billing_cycle` (`monthly` or `annual`).
2. The backend records a `checkout_sessions` row and a `payments` row (provider `polar`) and returns the plan's Polar checkout link with `reference_id=<our checkout_id>` and `customer_email` prefilled. Polar copies `reference_id` into the checkout, order and subscription metadata.
3. After payment Polar redirects to `/workspace/?view=payment-success&plan=<plan>&checkout_id=<Polar checkout id>`. `GET /api/billing/checkouts/{checkout_id}` accepts our ID or Polar's and reports `payment_pending` until the webhook arrives.

Checkout fails closed with HTTP 503 `payments_unavailable` (message asks the customer to email info@devbareun.com) while `POLAR_WEBHOOK_SECRET` is not set, so nobody can pay without the purchase being credited. `DEVBAREUN_PAYMENTS_ENABLED=false` closes checkout on purpose.

## Webhook

`POST /api/billing/webhook` on the Railway backend is registered in Polar for `order.paid`, `order.refunded` and the `subscription.*` events.

- The Standard Webhooks signature (`webhook-id`, `webhook-timestamp`, `webhook-signature`) is verified with `POLAR_WEBHOOK_SECRET`; timestamps older than 5 minutes are rejected.
- Events are claimed once through `claim_payment_webhook_event` (provider `polar`, event id `polar:<webhook-id>`) and completed with `complete_payment_webhook_event`. Failures return 4xx/5xx so Polar retries.
- The owner, plan and project come from the server-created checkout row matched by `reference_id`; the customer email from Polar is used only when no row matches.
- `order.paid` for Single Project grants one `analysis_credits` row (idempotent per order). For Plus and Pro it activates the subscription for the paid period.
- `subscription.*` events update the `subscriptions` row by Polar subscription id. A cancellation keeps access until the period end; `subscription.revoked` ends it. Usage resets when the billing period advances.
- `order.refunded` revokes an unused Single Project credit, or flags it `refund_review_required` when it was already used.

## Environment (Railway backend only)

- `POLAR_WEBHOOK_SECRET` (required to open checkout)
- Optional overrides: `POLAR_CHECKOUT_LINK_SINGLE`, `POLAR_CHECKOUT_LINK_PLUS_MONTHLY`, `POLAR_CHECKOUT_LINK_PLUS_ANNUAL`, `POLAR_CHECKOUT_LINK_PRO_MONTHLY`, `POLAR_CHECKOUT_LINK_PRO_ANNUAL`
- `DEVBAREUN_PAYMENTS_ENABLED` (default true)

No Polar access token is needed by the backend. Do not put payment secrets in Vercel.

## Database

The v1.4.31 migration (`database/2026_06_21_v1431_billing_lifecycle_integrity.sql`) is applied history and is not edited. Its claim functions store the provider name passed by the backend.
