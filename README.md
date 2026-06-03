# DevBareun v1.4.0 Production SaaS Core

DevBareun is a construction analytics and project control SaaS platform. The public frontend contains the approved landing experience, while the member workspace and backend provide authenticated project upload, analysis jobs, executive dashboards, report archive, billing, and usage control.

## Repository Layout

- `frontend/` - static landing pages and member workspace HTML/CSS/JS.
- `frontend/member-dashboard-app/` - React + Vite executive dashboard.
- `backend/app/` - FastAPI backend routes, auth dependencies, upload flow, analysis jobs, dashboard, billing, and reports.
- `database/` - Supabase PostgreSQL migrations and RLS policies.
- `docs/` - deployment, security, billing, and production SaaS notes.

## Frontend Local Run

```powershell
cd frontend
python -m http.server 4173
```

Open `http://127.0.0.1:4173/index.html`.

For the React executive dashboard:

```powershell
cd frontend/member-dashboard-app
npm install
npm run dev
```

## Backend Local Run

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health checks:

- `GET /api/health`
- `GET /api/saas/health`

## Environment Setup

Copy and configure:

- `backend/.env.example` in Railway or local backend env.
- `frontend/.env.example` in Vercel or local frontend env.

Frontend env values are public. Never place `SUPABASE_SERVICE_ROLE_KEY`, payment API keys, or webhook secrets in frontend files.

## Supabase Setup

1. Create a Supabase project.
2. Apply migrations in `database/` in order.
3. Create a private storage bucket named `project-files` or set `SUPABASE_STORAGE_BUCKET`.
4. Configure backend-only service role access in Railway.
5. Keep frontend limited to `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

## Lemon Squeezy Setup

Configure these backend variables:

- `PAYMENT_PROVIDER=lemon_squeezy`
- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`
- `LEMON_SQUEEZY_SINGLE_VARIANT_ID`
- `LEMON_SQUEEZY_PLUS_VARIANT_ID`
- `LEMON_SQUEEZY_PRO_VARIANT_ID`

Production flags must keep mock and pilot checkout disabled.

## Deployment

Vercel serves the static frontend from `frontend/`. Railway runs the FastAPI backend from `backend/` with:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required production flags:

- `DEVBAREUN_PRODUCTION_SECURITY=true`
- `DEVBAREUN_ENABLE_PILOT_LOGIN=false`
- `DEVBAREUN_ENABLE_DEV_AUTH=false`
- `DEVBAREUN_ENABLE_LOCAL_STORE=false`
- `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`
- `DEVBAREUN_ENABLE_PILOT_CHECKOUT=false`
- `DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false`
- `DEVBAREUN_DISABLE_DOCS=true`

## API Overview

- Auth: `/api/auth/*`
- Projects: `/api/projects`
- Uploads: `/api/uploads/*`
- Analysis jobs: `/api/analysis/*`
- Dashboard: `/api/dashboard/*`
- Billing: `/api/billing/*`
- Reports: `/api/reports/*`
- Health: `/api/health`, `/api/saas/health`

## Upload, Analyze, Dashboard Flow

1. User signs in through Supabase Auth.
2. Backend verifies the JWT and project ownership.
3. User creates a project.
4. Backend creates a signed Supabase Storage upload URL.
5. Frontend uploads to private storage and marks the file uploaded.
6. User starts a project review job.
7. Parser and analytics services save normalized results.
8. Executive dashboard reads the latest completed result.
9. Reports are generated from saved analysis results and archived.

## Production Security Checklist

- Configure CORS and checkout redirect allowlists.
- Keep docs disabled in production.
- Verify payment webhook signatures.
- Keep service role keys backend-only.
- Apply Supabase RLS policies.
- Use private storage buckets.
- Confirm member pages are `noindex`.
- Run backend compile/import checks and frontend build before deploy.

## Codex Task Starter

Use this at the beginning of Codex or agent tasks:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Do not recreate the project.
Do not duplicate existing files, pages, components, APIs, routes, styles, database tables, migrations, or configuration files.
Find the existing implementation and improve only the required part.

Task:
[write the exact task here]

Before coding:
- inspect existing files
- identify exact files to change
- avoid unrelated changes

After coding:
- list changed files
- explain what changed
- explain how to test
- mention risks or follow-up tasks
```
