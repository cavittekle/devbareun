# DevBareun Production SaaS Core

Version: 1.4.0

## 1. Architecture Overview

DevBareun is split into a public static frontend, a React executive dashboard, and a FastAPI backend. Supabase PostgreSQL is the production source of truth, Supabase Storage holds private project files and reports, Stripe handles checkout and subscriptions, Vercel hosts frontend assets, and Railway hosts the backend.

## 2. Data Flow

Public landing pages route users to login, registration, one-time upload, or the member workspace. The workspace uses `frontend/js/devbareun-api.js` for browser API calls. Backend protected routes verify the Supabase Auth token, load the user profile, enforce ownership, and persist project data in PostgreSQL.

## 3. Auth Flow

Supabase Auth is the production default. The backend accepts the bearer JWT, verifies it, loads `users_profile`, and applies role/status checks. Pilot login and dev auth are blocked when `DEVBAREUN_PRODUCTION_SECURITY=true`.

## 4. Upload Flow

1. User creates or opens a project.
2. Frontend requests `POST /api/uploads/create-url`.
3. Backend validates filename, extension, MIME type, file size, and project ownership.
4. Backend creates a private signed Supabase Storage upload URL.
5. Frontend uploads the file and calls `POST /api/uploads/mark-uploaded`.
6. Backend records metadata in `uploaded_files`.

## 5. Analysis Job Flow

`POST /api/analysis/start/{project_id}` creates a queued job, validates ownership, confirms files exist, checks subscription or credits, and runs parser/analytics work in a background task. Credits or monthly usage are consumed only after a successful completion. Failed jobs keep a safe error message and do not consume usage.

## 6. Dashboard Flow

The React executive dashboard calls:

- `GET /api/dashboard/portfolio`
- `GET /api/dashboard/executive/{project_id}`

If no completed result exists, the UI shows an empty state. In development, demo data remains available as a fallback so the approved visual design is not blocked by backend setup.

## 7. Billing and Credit Flow

Stripe checkout routes support one-time project analysis, Plus, and Pro plans. Webhooks must be signed in production. Stripe event ids are stored to prevent duplicate processing. Usage checks happen before job start, while usage is consumed after successful job completion.

## 8. Report Archive Flow

Reports are generated from saved analysis results, stored through the configured report storage flow, and recorded in the `reports` table. Download routes require report ownership.

## 9. Deployment Checklist

- Apply database migrations in `database/`.
- Create private Supabase Storage bucket `project-files`.
- Configure Railway backend env from `backend/.env.example`.
- Configure Vercel frontend env from `frontend/.env.example`.
- Set allowed origins and checkout redirect origins.
- Set Stripe price ids and webhook secret.
- Run backend compile/import checks.
- Run React dashboard build.
- Verify `/api/health` and `/api/saas/health`.

## 10. Security Checklist

- `DEVBAREUN_PRODUCTION_SECURITY=true`
- `DEVBAREUN_ENABLE_PILOT_LOGIN=false`
- `DEVBAREUN_ENABLE_DEV_AUTH=false`
- `DEVBAREUN_ENABLE_LOCAL_STORE=false`
- `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`
- `DEVBAREUN_ENABLE_PILOT_CHECKOUT=false`
- `DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false`
- `DEVBAREUN_DISABLE_DOCS=true`
- CORS allowlist configured.
- Service role key kept backend-only.
- Stripe webhook signature required.
- RLS policies applied.
- Private dashboard pages marked `noindex`.

## 11. Known Limitations

- The current rate limiter is process-local. Use Redis or Upstash before multi-instance production scaling.
- Local JSON project flow is retained only for older one-time project compatibility and should remain disabled in production.
- Dashboard API uses latest completed saved analysis result; richer time-series reporting can be expanded after more production data is collected.
- Asset conversion to WebP/SVG should be done with visual review to avoid damaging the approved brand marks.

## 12. Next Steps

- Add automated CI for backend route tests and frontend builds.
- Add Supabase integration tests with a staging project.
- Add production log drains and alerting.
- Add report template versioning.
- Add admin audit views for billing, uploads, and project review events.

