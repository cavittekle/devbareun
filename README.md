# DevBareun

DevBareun is a construction analytics and project control SaaS platform.

## Architecture

- Public website: static HTML/CSS/JS in `frontend/`
- Customer workspace: React/Vite in `frontend/member-dashboard-app/`
- Backend API: FastAPI in `backend/`
- Database, auth, and private file storage: Supabase
- Checkout and billing webhooks: Lemon Squeezy

| Target   | Root directory | Notes                              |
| -------- | -------------- | ---------------------------------- |
| Vercel   | `frontend`     | Config in `frontend/vercel.json`   |
| Railway  | `backend`      | Health check `/api/health`         |
| Supabase | `database`     | Order in `database/SUPABASE_DEPLOY_ORDER.md` |

The repository root is not a deploy target and intentionally has no `index.html`. See `docs/DEPLOYMENT_ROOTS.md`.

## Repository Layout

- `frontend/` - public website, Vercel config, and workspace build script.
- `frontend/member-dashboard-app/` - React workspace source (login, projects, uploads, reports, billing, settings).
- `frontend/workspace/` - generated build output; do not edit or commit.
- `backend/app/` - FastAPI routes, auth, uploads, analysis jobs, billing, and reports.
- `backend/tests/` - backend tests.
- `database/` - Supabase schema, migrations, and RLS policies.
- `docs/` - deployment, environment, security, and checklists.
- `tools/` - release gate, env validation, smoke tests, and packaging.

## Local Development

Requires Node.js 22 and Python 3.12.

```powershell
# Public website -> http://127.0.0.1:4173/index.html
cd frontend
python -m http.server 4173

# React workspace (dev server) -> http://127.0.0.1:5174/workspace/
cd frontend/member-dashboard-app
npm ci
npm run dev

# Build the workspace into frontend/workspace/
cd frontend
npm ci
npm run build

# Backend API -> http://127.0.0.1:8000/api/health
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET /api/readiness` returns secret-safe release errors and warnings.

## Environment

- `frontend/.env.example` - public Vercel variables only.
- `backend/.env.example` - Railway variables and private secrets.

Never put `SUPABASE_SERVICE_ROLE_KEY`, payment API keys, webhook secrets, database passwords, or JWT secrets in frontend files, Vercel variables, or Git. Full list: `docs/ENVIRONMENT_VARIABLES.md`.

## Supabase

1. Apply SQL from `database/` in the order given by `database/SUPABASE_DEPLOY_ORDER.md`.
2. Create private storage buckets `project-files` and (if report archiving is used) `reports`.
3. Set the service role key in Railway only.

Uploads use private Supabase Storage signed URLs; Railway's filesystem is ephemeral and must not hold uploads.

## Payments

Production uses Lemon Squeezy. Railway variables:

- `DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy`
- `LEMON_SQUEEZY_API_KEY`, `LEMON_SQUEEZY_STORE_ID`, `LEMON_SQUEEZY_WEBHOOK_SECRET`
- `LEMON_SQUEEZY_SINGLE_VARIANT_ID`, `LEMON_SQUEEZY_PLUS_VARIANT_ID`, `LEMON_SQUEEZY_PRO_VARIANT_ID`

Webhook URL: `https://devbareun-production.up.railway.app/api/billing/webhook`

Mock payment, pilot checkout, local storage, and development auth must stay disabled in production.

## Checks

The same checks run in GitHub Actions (`.github/workflows/ci.yml`):

```powershell
python tools/release_gate.py --root .
python tools/validate_production_env.py --backend-env backend/.env.example --frontend-env frontend/.env.example --allow-placeholders
cd frontend; npm run check; cd ..
cd backend; python -m pytest; cd ..
```

After a deploy, smoke-test the live services:

```powershell
python tools/smoke_deploy.py --frontend-url https://devbareun.com --backend-url https://devbareun-production.up.railway.app --strict --retries 3
```

A configured backend reports `"database": "connected"` and `"storage": "configured"` at `/api/health`. `not_configured` means Supabase setup is incomplete.

## Going Live

Follow `docs/LIVE_DEPLOY_CHECKLIST.md` and `docs/LIVE_SUPABASE_PAYMENT_CHECKLIST.md`. Local checks do not replace provider-side validation.
