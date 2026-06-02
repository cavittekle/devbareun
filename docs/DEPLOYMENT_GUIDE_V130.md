# DevBareun Live Deployment Guide

## Frontend: Vercel

Recommended setup:

- Project root: repository root
- Vercel Root Directory: `frontend`
- Framework Preset: Other
- Build Command: leave empty
- Output Directory: leave empty
- Config file: `frontend/vercel.json`

After deployment, connect:

- `devbareun.com`
- `www.devbareun.com`

Redirect `www` to apex in Vercel domain settings if needed.

## Backend: Railway

Recommended setup:

- Root Directory: `backend`
- Runtime: Python 3.12
- Start Command: from `backend/railway.json`
- Healthcheck Path: `/api/saas/health`

Railway must have all backend variables from `backend/.env.example`.

## Supabase

Use `docs/SUPABASE_SETUP_GUIDE.md`.

Minimum launch requirements:

- SQL migrations applied.
- Private storage bucket created.
- Supabase Auth enabled.
- `SUPABASE_SERVICE_ROLE_KEY` exists only in Railway.

## Stripe

Use `docs/STRIPE_SETUP_GUIDE.md`.

Minimum launch requirements:

- Test mode checkout works for Single Project.
- Test mode subscription checkout works for Plus and Pro.
- Webhook reaches Railway and signature verification passes.
- Production mock payment is disabled.

## Release Order

1. Create Supabase project and run SQL.
2. Create Stripe products and webhook in test mode.
3. Deploy Railway backend with production security enabled.
4. Verify `GET /health`.
5. Verify `GET /api/saas/health`.
6. Deploy Vercel frontend from `frontend`.
7. Add production domains to CORS and checkout allow-list.
8. Test Single Project upload and checkout.
9. Test Plus account creation, login, billing and workspace access.
10. Test Pro account creation, login, billing and workspace access.
11. Switch Stripe keys and price IDs to live mode.
12. Re-test one low-value live checkout before public launch.
