# v1.3.8 Billing Gate Setup

## Flow
1. User logs in.
2. Frontend calls `GET /api/workspace/entitlements`.
3. User chooses Single, Plus or Pro from `billing.html`.
4. Backend creates Stripe checkout session.
5. Stripe webhook activates payment and credits.
6. Analyze endpoint accepts either paid project access or authenticated workspace credit.
7. Generated output is saved to report archive and can be printed in A4/A3.

## Required environment variables

```bash
STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SINGLE_PROJECT_PRICE_ID=price_...
STRIPE_PLUS_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...
PUBLIC_SITE_URL=https://devbareun.com
SUPABASE_URL=https://...supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

## Pilot mode
Without Stripe keys, checkout creation returns a pilot checkout record. The `checkout.html` page can activate it for staging tests. Disable pilot activation before commercial production.
