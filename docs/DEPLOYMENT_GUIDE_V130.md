
# DevBareun v1.3.0 Deployment Guide

## Frontend

Keep the current Vercel configuration:

- Root Directory: `frontend`
- Framework: static/other unless migrated to Next.js later
- Environment: `VITE_API_URL`

## Backend

Keep Railway backend:

- Root Directory: `backend`
- Start command: use existing Railway/FastAPI configuration
- Add Supabase and Stripe variables before production launch

## Database

Use Supabase PostgreSQL with the SQL files in `/database`.

## Recommended release order

1. Deploy backend v1.3.0.
2. Verify `/health` shows `1.3.0-saas-foundation`.
3. Verify `/api/saas/health`.
4. Configure Supabase schema.
5. Configure Stripe test mode.
6. Test Single Project guest flow in test mode.
7. Test Plus/Pro subscription flow.
8. Enable production payment and disable mock payment.
