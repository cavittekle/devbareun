# DevBareun Deployment Guide

DevBareun uses separate deploy roots for the public frontend and backend API.

## Deploy Roots

- Vercel Root Directory: `frontend`
- Railway Root Directory: `backend`
- Supabase SQL: `database`

Do not deploy the repository root as a production app.

## Frontend

Deploy `frontend` to Vercel. The public website is static HTML/CSS/JS and uses:

- `frontend/vercel.json`
- `frontend/index.html`
- `frontend/css/modern-landing.css`
- `frontend/js/modern-landing.js`

Production domain:

- `https://devbareun.com`
- `https://www.devbareun.com`

## Backend

Deploy `backend` to Railway. The API starts with:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required production checks:

- `/api/health` returns `database: connected`
- `/api/health` returns `storage: configured`
- `/api/saas/health` returns `status: ok`

## Production Environment

Backend secrets must stay in Railway only:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`

Frontend may only use public Supabase values.

## References

- `docs/DEPLOYMENT_ROOTS.md`
- `docs/LIVE_DEPLOY_CHECKLIST.md`
- `docs/LIVE_SUPABASE_PAYMENT_CHECKLIST.md`
