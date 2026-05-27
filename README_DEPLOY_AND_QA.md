# DevBareun v1.3.8 — Admin Panel Package

## Live deploy preparation

Use these files for the current production-readiness pass:

- `backend/.env.example` for Railway backend variables.
- `frontend/.env.example` for public Vercel frontend variables.
- `frontend/vercel.json` for static frontend deploy settings.
- `backend/railway.json` for FastAPI start command and healthcheck.
- `docs/LIVE_DEPLOY_CHECKLIST.md` for the final launch checklist.
- `docs/ENVIRONMENT_VARIABLES.md` for the full secret/public variable map.

Production must keep mock payment and pilot-only flows disabled.

This package follows the corrected roadmap: **v1.3.8 is Admin Panel**. The billing/usage foundation remains in the codebase because the admin console needs payments and credit data, but the official release focus is the protected operations panel.

## New admin files

- `frontend/admin.html`
- `frontend/js/admin-panel.js`
- `frontend/css/admin-panel.css`
- `database/2026_05_27_v138_admin_panel.sql`
- `docs/ADMIN_PANEL_V138.md`

## Admin modules

Users, companies, projects, payments, reports, failed uploads, credit usage and activity logs are available from `/admin.html`.

## Required environment variable for production admins

Set admin emails in Railway/Vercel as needed:

```bash
DEVBAREUN_ADMIN_EMAILS=admin@devbareun.com,cavid@yourdomain.com
```

Supabase users can also be admins if their user metadata includes `is_admin: true`.

---

# DevBareun Combined AgentOps Package v1.1.3

This package includes:

- `frontend/` — DevBareun frontend package
- `backend/` — DevBareun backend package
- `agents/devbareun_ops_engine/` — active DevBareun AgentOps system
- `tools/github_auto_upload.py` — safe GitHub sync tool for frontend/backend repositories

## Fixed release status

```text
Version: 1.1.3-fixed-release
Blocking Python/AgentOps crashes: fixed
SEO robots.txt issue: fixed
Parser template KPI priority: fixed
Runtime data/storage in ZIP: removed
GitHub clean-sync support: added
```

AgentOps may still show warnings locally when deployment secrets are not exported. Those are external configuration warnings, not package-code crashes.

## Recommended deployment

### Backend

Upload the contents of `backend/` to the `devbareun-backend` repository / Railway service.

Railway start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Minimum Railway environment variables:

```text
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,http://localhost:3000,http://localhost:5173
DEVBAREUN_MAX_FILES=12
DEVBAREUN_MAX_FILE_MB=30
DEVBAREUN_MAX_TOTAL_MB=120
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
```

For commercial launch, configure Stripe and set:

```text
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
STRIPE_SECRET_KEY=...
STRIPE_SINGLE_PROJECT_PRICE_ID=...
STRIPE_PLUS_PRICE_ID=...
STRIPE_PRO_PRICE_ID=...
STRIPE_WEBHOOK_SECRET=...
```

### Frontend

Upload the contents of `frontend/` to the `devbareun-frontend` repository / Vercel project.

### AgentOps local run example

From the package root that contains `frontend/`, `backend/`, and `agents/`:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports
```

Strict mode:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports --strict
```

Generated reports:

```text
agent_reports/agentops_supervisor_report.md
agent_reports/agentops_supervisor_report.json
agent_reports/construction_marketing_research.json
agent_reports/release_notes_v1_1_3_fixed_release.json
```

## GitHub auto-upload

Dry run:

```bash
python tools/github_auto_upload.py --root . --dry-run
```

Safe PR sync:

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python tools/github_auto_upload.py --root .
```

Clean sync, which also removes old files from target repos when they no longer exist locally:

```bash
python tools/github_auto_upload.py --root . --clean
```

Do not commit API keys, tokens, Railway secrets, Vercel secrets, Stripe secrets, OpenAI keys, or `.env` files to GitHub.

## v1.3.7 report archive deployment note

Apply the Supabase migration below before enabling production report archive persistence:

```sql
-- database/2026_05_27_v137_report_archive_print.sql
```

New frontend files:

```text
frontend/css/report-print.css
frontend/js/report-print-system.js
```

New backend behavior:

```text
GET  /api/workspace/reports
GET  /api/workspace/reports/{report_id}
POST /api/workspace/reports/archive
GET  /api/projects/{project_id}/report/pdf?paper=a4|a3
```

A4 print is portrait. A3 print is landscape and is intended for wide dashboard/report review.


## v1.3.8 QA addendum
- Login to workspace and verify entitlement cards update.
- Open Billing and create Single / Plus / Pro checkout.
- In pilot mode, activate checkout from checkout page.
- Run analysis with Authorization bearer and confirm report appears in Report Archive.
- Download PDF/Excel from report archive using authenticated buttons.


## v1.3.9 Production Security

This package adds the security layer required before the Real SaaS Launch Package:

- Apply `database/2026_05_27_v139_production_security.sql` in Supabase.
- Set `DEVBAREUN_ENV=production` and `DEVBAREUN_PRODUCTION_SECURITY=true`.
- Set `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
- Set `STRIPE_WEBHOOK_SECRET` and keep unsigned webhooks disabled.
- Keep Supabase Storage private and use backend signed download URLs.
- Use explicit admin allow-list or Supabase admin metadata for admin panel access.

See `docs/PRODUCTION_SECURITY_V139.md` for details.
