# Stripe Setup Guide

## Products And Prices

Create these Stripe products and prices:

1. Single Project: one-time payment, `$29`
2. Plus: monthly subscription, `$49`, 5 projects per month
3. Pro: monthly subscription, `$89`, 20 projects per month

## Backend Variables

Set in Railway:

```env
STRIPE_SECRET_KEY=sk_live_or_test_replace_me
STRIPE_WEBHOOK_SECRET=whsec_replace_me
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

Production rules:

- Set `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
- Set `DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false`.
- Add the real webhook signing secret to `STRIPE_WEBHOOK_SECRET`.
- Use test mode first, then switch price IDs and keys to live mode after checkout is verified.
