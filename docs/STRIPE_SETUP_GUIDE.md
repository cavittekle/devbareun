# Stripe Setup Guide

## Products And Prices

Create these Stripe products and prices:

1. Single Project: one-time payment, `$29`
2. Plus: monthly subscription, `$49`, 5 projects per month
3. Pro: monthly subscription, `$89`, 20 projects per month

## Backend Variables

Set in Railway:

```env
STRIPE_SECRET_KEY=replace_with_stripe_secret_key
STRIPE_WEBHOOK_SECRET=replace_with_stripe_webhook_secret
STRIPE_SINGLE_PROJECT_PRICE_ID=price_single_project
STRIPE_PLUS_PRICE_ID=price_plus_monthly
STRIPE_PRO_PRICE_ID=price_pro_monthly
STRIPE_SINGLE_PROJECT_AMOUNT_CENTS=2900
STRIPE_CURRENCY=usd
```

The legacy single-project endpoint still reads these fallback variables:

```env
STRIPE_PRICE_ID=price_single_project
DEVBAREUN_STRIPE_AMOUNT_CENTS=2900
DEVBAREUN_STRIPE_CURRENCY=usd
```

## Webhook

Create one Stripe webhook endpoint:

```text
https://YOUR_RAILWAY_BACKEND_DOMAIN/api/payments/webhook
```

Enable these events:

- `checkout.session.completed`
- `payment_intent.succeeded`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Single Project Upload Flow

The public landing page uses this paid guest flow:

1. Visitor selects Single Project or opens `index.html?plan=single#upload`.
2. Visitor uploads project files on the landing upload panel.
3. DevBareun creates a guest project record and uploads the files.
4. DevBareun shows a mapping preview.
5. The button changes to `Pay $29 & Generate Dashboard`.
6. Backend creates a Stripe Checkout session with `metadata.project_id`.
7. Stripe redirects back to `payment-success.html?plan=single&guest=1&project_id=...`.
8. Stripe webhook marks that project as paid.
9. The success page generates the dashboard and opens `result-dashboard.html`.

This means Single Project does not need an account, but dashboard generation stays locked until payment is confirmed.

Production rules:

- Set `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
- Set `DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false`.
- Add the real webhook signing secret to `STRIPE_WEBHOOK_SECRET`.
- Use test mode first, then switch price IDs and keys to live mode after checkout is verified.
