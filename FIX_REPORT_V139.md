# DevBareun v1.3.9 — Production Security Fix Report

## Completed

- Added `backend/app/security_runtime.py`.
- Added API rate-limit middleware and production security headers.
- Hardened mock payment so it is disabled in production security mode.
- Hardened admin role fallback behavior.
- Hardened protected file download URL generation.
- Enforced Stripe webhook signature requirements.
- Added secure guest token validation and TTL clamp.
- Added strict Supabase RLS migration.
- Updated `.env.example` and production security documentation.

## Important deployment note

Run this migration before production:

`database/2026_05_27_v139_production_security.sql`

Then set production env vars and keep Supabase Storage bucket private.
