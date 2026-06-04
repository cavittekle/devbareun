# DevBareun v1.4.0 Production SaaS Core

DevBareun is a construction analytics and project control SaaS platform. The production frontend is static HTML/CSS/JS and the backend is FastAPI.

The repository root is not a deploy target. There is intentionally no root `index.html`.

## Deploy Roots

- Vercel Root Directory: `frontend`
- Railway Root Directory: `backend`
- Supabase SQL: `database`

See `docs/DEPLOYMENT_ROOTS.md` before deploying.

## Repository Layout

- `frontend/` - production static landing pages and member workspace HTML/CSS/JS.
- `backend/app/` - FastAPI backend routes, auth, uploads, analysis jobs, dashboards, billing, and reports.
- `database/` - Supabase PostgreSQL schema, migrations, seeds, and RLS policies.
- `docs/` - deployment, environment, billing, security, and production checklists.

## Frontend Local Run

```powershell
cd frontend
python -m http.server 4173
```

Open `http://127.0.0.1:4173/index.html`.

## Backend Local Run

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health checks:

- `GET /api/health`
- `GET /api/saas/health`

## Environment Setup

- Use `frontend/.env.example` only for public Vercel/frontend variables.
- Use `backend/.env.example` for Railway/backend variables and private secrets.
- Root `.env.example` is only a pointer and should not contain runtime secrets.

Never place `SUPABASE_SERVICE_ROLE_KEY`, payment API keys, webhook secrets, database passwords, or JWT secrets in frontend files or Vercel variables.

## Supabase Setup

1. Create a Supabase project.
2. Apply SQL from `database/` using `database/SUPABASE_DEPLOY_ORDER.md`.
3. Create private storage bucket `project-files`.
4. Create private storage bucket `reports` if report archive storage is used.
5. Configure backend-only service role access in Railway.
6. Keep frontend limited to public Supabase values only.

## Payment Setup

Production checkout uses Lemon Squeezy.

Required Railway variables:

- `DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy`
- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_STORE_ID`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`
- `LEMON_SQUEEZY_SINGLE_VARIANT_ID`
- `LEMON_SQUEEZY_PLUS_VARIANT_ID`
- `LEMON_SQUEEZY_PRO_VARIANT_ID`

Webhook URL:

```text
https://devbareun-production.up.railway.app/api/billing/webhook
```

## Deployment Checklist

Before live launch, complete:

- `docs/LIVE_DEPLOY_CHECKLIST.md`
- `docs/LIVE_SUPABASE_PAYMENT_CHECKLIST.md`

Expected live backend health after Supabase is configured:

```json
{
  "status": "ok",
  "database": "connected",
  "storage": "configured"
}
```

If health shows `database: not_configured` or `storage: not_configured`, Supabase live setup is not complete.
