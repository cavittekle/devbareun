# DevBareun v1.3.1 — Stripe Payment + Credit Enforcement

This phase keeps the existing DevBareun design and adds SaaS payment/credit logic around it.

## Plans

| Plan | Payment type | Credits |
|---|---:|---:|
| Single Project | One-time Checkout | 1 project analysis |
| Plus | Monthly subscription | 5 project analyses/month |
| Pro | Monthly subscription | 20 project analyses/month |

## Environment variables

```bash
PUBLIC_SITE_URL=https://devbareun.com
STRIPE_SECRET_KEY=sk_live_or_test
STRIPE_WEBHOOK_SECRET=whsec_live_or_test
STRIPE_SINGLE_PROJECT_PRICE_ID=price_xxx
STRIPE_PLUS_PRICE_ID=price_xxx
STRIPE_PRO_PRICE_ID=price_xxx
STRIPE_SINGLE_PROJECT_AMOUNT_CENTS=2900
STRIPE_CURRENCY=usd
```

## New/updated API routes

```text
POST /api/payments/create-one-time-checkout
POST /api/payments/create-subscription-checkout
POST /api/payments/webhook
POST /api/payments/activate-pilot-checkout   # pilot only
GET  /api/credits/status
POST /api/analysis/create                    # now checks credits
```

## Production notes

- Use real Stripe price IDs for Plus and Pro.
- Set webhook endpoint in Stripe dashboard to `/api/payments/webhook`.
- Disable or protect `/api/payments/activate-pilot-checkout` before production launch.
- Supabase/PostgreSQL should replace the JSON pilot store before commercial launch.
- Keep Stripe secret keys only in backend environment variables.
