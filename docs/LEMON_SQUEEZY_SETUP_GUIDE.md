# Lemon Squeezy Setup Guide

Use Lemon Squeezy when Stripe account country support is not available.

## Products And Variants

Create these products in Lemon Squeezy:

1. `DevBareun Single Project`: one-time payment, `$29`
2. `DevBareun Plus`: monthly subscription, `$49`, 5 projects per month
3. `DevBareun Pro`: monthly subscription, `$89`, 20 projects per month

Copy each product variant ID. DevBareun uses variant IDs to create hosted checkouts.

Current test-mode variant IDs:

```text
LEMON_SQUEEZY_SINGLE_VARIANT_ID=1741208
LEMON_SQUEEZY_PLUS_VARIANT_ID=1741246
LEMON_SQUEEZY_PRO_VARIANT_ID=1741254
```

## Backend Variables

Set these in Railway:

```env
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=replace_with_api_key
LEMON_SQUEEZY_STORE_ID=replace_with_store_id
LEMON_SQUEEZY_WEBHOOK_SECRET=replace_with_webhook_signing_secret
LEMON_SQUEEZY_SINGLE_VARIANT_ID=replace_with_single_project_variant_id
LEMON_SQUEEZY_PLUS_VARIANT_ID=replace_with_plus_variant_id
LEMON_SQUEEZY_PRO_VARIANT_ID=replace_with_pro_variant_id
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false
DEVBAREUN_PRODUCTION_SECURITY=true
PUBLIC_SITE_URL=https://devbareun.com
```

Do not put Lemon Squeezy API keys or webhook secrets in Vercel.

## Webhook

Create one Lemon Squeezy webhook endpoint:

```text
https://devbareun-production.up.railway.app/api/billing/webhook
```

Select these events:

- `order_created`
- `subscription_created`
- `subscription_updated`
- `subscription_cancelled`
- `subscription_resumed`
- `subscription_expired`
- `subscription_payment_success`
- `subscription_payment_failed`

Copy the webhook signing secret into `LEMON_SQUEEZY_WEBHOOK_SECRET`.

## Test Flow

1. Enable Lemon Squeezy test mode.
2. Create the three products and copy their variant IDs.
3. Set Railway variables and redeploy the backend.
4. Start checkout from DevBareun.
5. Confirm Lemon Squeezy redirects back to `https://devbareun.com`.
6. Confirm the webhook event is delivered successfully.

## Notes

The existing DevBareun frontend continues calling `/api/billing/create-one-time-checkout` and `/api/billing/create-subscription-checkout`.
The backend chooses Lemon Squeezy when `DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy`.
