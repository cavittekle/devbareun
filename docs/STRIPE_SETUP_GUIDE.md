
# Stripe Setup Guide

Create three Stripe products/prices:

1. Single Project — one-time payment
2. Plus — monthly subscription, 5 project analyses/month
3. Pro — monthly subscription, 20 project analyses/month

Backend environment variables:

```env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_SINGLE_PRICE_ID=
STRIPE_PLUS_PRICE_ID=
STRIPE_PRO_PRICE_ID=
```

Webhook events to handle:

- `checkout.session.completed`
- `payment_intent.succeeded`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Webhook responsibilities:

- mark Single Project payment as paid
- activate guest result access
- activate Plus/Pro subscription
- reset monthly credits on renewal
- restrict access when payment fails or subscription is canceled
