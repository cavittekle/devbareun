# DevBareun

DevBareun is a construction analytics and project control SaaS platform.

## Architecture

The production architecture is:

- Public website: static HTML/CSS/JS in `frontend/`
- Customer workspace app: React/Vite in `frontend/member-dashboard-app/`
- Backend API: FastAPI in `backend/`
- Database, authentication, and private file storage: Supabase
- Checkout, subscriptions, and billing webhooks: Lemon Squeezy

The repository root is not a deploy target. There is intentionally no root `index.html`.

## Deploy Roots

- Vercel Root Directory: `frontend`
- Railway Root Directory: `backend`
- Supabase SQL: `database`

See `docs/DEPLOYMENT_ROOTS.md` before deploying.

## Repository Layout

- `frontend/` - public website, Vercel configuration, and frontend build orchestration.
- `frontend/member-dashboard-app/` - production React/Vite customer workspace source.
- `frontend/workspace/` - generated workspace build output; do not edit or commit it.
- `backend/app/` - FastAPI backend routes, auth, uploads, analysis jobs, dashboards, billing, and reports.
- `backend/tests/` - backend release and security tests.
- `database/` - Supabase PostgreSQL schema, migrations, owner promotion, and RLS policies.
- `docs/` - deployment, environment, billing, security, and production checklists.
- `tools/` - release packaging, smoke testing, and production-readiness checks.

## Local Development

Recommended versions:

- Node.js 22
- Python 3.12

### Public Website

```powershell
cd frontend
python -m http.server 4173
```

Open `http://127.0.0.1:4173/index.html`.

### React Workspace

```powershell
cd frontend/member-dashboard-app
npm ci
npm run dev
```

Open the Vite URL printed by the command, normally `http://127.0.0.1:5174/workspace/`.

The React app is the source of truth for login, registration, overview, uploads, projects, reports, billing, settings, and result views. Retired static workspace URLs are redirected through `frontend/vercel.json`.

### Integrated Frontend Build

Run this from `frontend/` to install the workspace dependencies, build the React app, and copy its generated output to `frontend/workspace/`:

```powershell
cd frontend
npm ci
npm run build
```

Do not edit `frontend/workspace/` directly.

### Backend API

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health checks:

- `GET /api/health`
- `GET /api/saas/health`
- `GET /api/version`
- `GET /api/readiness`
- `GET /api/analysis/operations` (staff only; worker queue/liveness)

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

Production uploads use private Supabase Storage signed URLs. Railway filesystem storage is ephemeral and must not be used as the permanent production upload store.

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

Keep mock payment, pilot checkout, local storage, and development authentication disabled in production. Live provider credentials are configured in provider dashboards and Railway, never in Git.

## Verification

Release gate and env-example validation:

```powershell
python tools/release_gate.py --root .
python tools/validate_production_env.py --backend-env backend/.env.example --frontend-env frontend/.env.example --allow-placeholders
```

Frontend build:

```powershell
cd frontend
npm run check
```

Backend checks:

```powershell
python -m compileall backend/app agents/devbareun_ops_engine tools
python -m pytest backend/tests
```

Clean release package:

```powershell
python tools/package_release.py --root .
```

GitHub Actions validates the release gate, env examples, committed environment files, obvious secret formats, the React workspace build, Python syntax, and backend tests. The workflow is defined in `.github/workflows/ci.yml`.

## Deployment Checklist

Before live launch, complete:

- `docs/ADMIN_ROLES.md`
- `docs/DEPLOYMENT.md`
- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/QA_CHECKLIST.md`
- `docs/LIVE_DEPLOY_CHECKLIST.md`
- `docs/LIVE_SUPABASE_PAYMENT_CHECKLIST.md`
- `docs/SUPER_ADMIN_WORKSPACE.md`

Expected live backend health after Supabase is configured:

```json
{
  "status": "ok",
  "database": "connected",
  "storage": "configured"
}
```

If health shows `database: not_configured` or `storage: not_configured`, Supabase live setup is not complete.

Live Supabase, Lemon Squeezy, Railway, Vercel, storage, RLS, and owner-account setup must be completed and verified separately. Local checks do not replace provider-side production validation.

## v1.4.8 production readiness checks

Before a public deployment, validate env files and smoke-test live services:

```bash
python tools/validate_production_env.py --backend-env backend/.env.production --frontend-env frontend/.env.production
python tools/smoke_deploy.py --frontend-url https://devbareun.com --backend-url https://devbareun-production.up.railway.app --strict --retries 3
```

The backend also exposes `GET /api/readiness`, which returns secret-safe release errors and warnings. See `docs/PRODUCTION_READINESS_V148.md`.


## Production pilot acceptance

After deployment, run the guarded authenticated acceptance tool with a dedicated pilot account. It is read-only by default; write, analysis and report actions require explicit confirmation flags. See `docs/PILOT_ACCEPTANCE_V1427.md`.
