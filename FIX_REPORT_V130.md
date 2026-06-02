
# DevBareun v1.3.0 — SaaS Foundation

## Scope

This release converts the existing DevBareun project structure toward a real SaaS platform without recreating or replacing the current website design.

## Added

- Supabase PostgreSQL schema
- RLS starter policies
- plan seed data for Single / Plus / Pro
- SaaS API skeleton routes
- Guest one-time project flow
- Project ID / File ID / Analysis ID / Report ID helpers
- Local pilot SaaS store for development
- Stripe-ready checkout and webhook placeholder routes
- Admin API skeleton
- SaaS setup and deployment guides
- Frontend placeholder pages preserving DevBareun visual shell

## Not yet production-complete

- Supabase Auth token validation must be connected
- Supabase Storage upload must replace metadata-only SaaS upload skeleton
- Stripe Checkout sessions must be created with real price IDs
- Stripe webhook signature verification must be enabled
- Admin endpoints must be protected

## Next release recommendation

v1.3.1 — Stripe Payment + Credit Enforcement
