# DevBareun v1.4.14 Production Deployment Runbook

This runbook is the operator checklist for promoting the clean source package to production. It assumes the source package has already passed release gate, API contract, database contract, asset checks, frontend build and backend tests.

## 0. Release artifact

Use the current clean source package, not the original development archive. The clean package must include source, database migrations, docs, tools, templates, `frontend/assets/`, and `frontend/workspace/`, but must not include `.venv/`, `node_modules/`, `.git/`, `dist/`, cache files or runtime `.env` files.

Local release gate before provider work:

```bash
python tools/release_gate.py --root . --strict-package-tree
python tools/check_frontend_assets.py --root .
python tools/check_frontend_deploy_surface.py --root . --strict
python tools/check_template_manifest.py --root .
python tools/check_database_contract.py --root .
python tools/check_deploy_runbook.py --root .
python tools/export_api_contract.py --root . --check --output /tmp/devbareun-api-contract.json
python tools/validate_production_env.py --backend-env backend/.env.example --frontend-env frontend/.env.example --allow-placeholders
```

## 1. Supabase database and storage

Open Supabase SQL Editor and run the deploy order exactly as documented in `database/SUPABASE_DEPLOY_ORDER.md`:

1. `2026_05_29_v140_production_saas_core.sql`
2. `2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `2026_06_08_v141_super_admin_workspace.sql`
4. `2026_06_18_v142_canonical_api_bridge.sql`
5. `2026_06_18_v145_analysis_worker.sql`
6. `2026_06_19_v1413_database_contract_bridge.sql`
7. `2026_06_19_v1416_analysis_worker_observability.sql`
8. `2026_06_19_v1417_analysis_job_recovery.sql`
9. `seed_plans.sql`
10. `promote_owner_info_devbareun.sql` after `info@devbareun.com` or the chosen owner account exists in Supabase Auth
11. `production_rls_audit.sql` as the read-only verification query

Run the static schema check locally before and after editing migrations:

```bash
python tools/check_database_contract.py --root .
```

Create private Supabase Storage buckets:

```text
project-files
reports
```

Both buckets must remain private. Do not expose storage objects publicly; the backend issues signed upload/download URLs.

## 2. Railway web service

Create or update the Railway backend web service from the same repository/package.

Required service settings:

```text
Root Directory = backend
Start Command = python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Minimum production runtime flags:

```text
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_REQUIRE_CSRF_TOKEN=true
DEVBAREUN_ANALYSIS_JOB_MODE=worker
DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS=3
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=false
DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD=false
DEVBAREUN_DISABLE_DOCS=true
DEVBAREUN_RATE_LIMIT_ENABLED=true
DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false
```

Railway backend must also receive Supabase private values, Lemon Squeezy private values and Upstash Redis values listed in `docs/DEPLOYMENT_ENV_MATRIX_V1414.md`.

Do not place Supabase service role, Supabase JWT secret, Lemon Squeezy API key, Lemon Squeezy webhook secret, Upstash token or database passwords in Vercel/frontend env values.

## 3. Railway worker service

Create a second Railway service from the same backend root for analysis jobs. This service must use the same backend environment variables as the web service, especially Supabase service role, storage bucket names and Lemon Squeezy settings.

Required service settings:

```text
Root Directory = backend
Start Command = python -m app.analysis_worker --loop --interval 10 --batch-size 1
```

The repository includes `backend/railway.worker.json` as the worker reference. Durable production analysis requires:

```text
DEVBAREUN_ANALYSIS_JOB_MODE=worker
```

The API will enqueue `analysis_jobs`; the Railway worker service claims queued jobs, sends heartbeats, retries stale jobs and writes `analysis_results`/`risks`.


### Worker liveness verification

After the worker starts, authenticate as a staff user and call:

```bash
curl -H "Authorization: Bearer <staff-access-token>" \
  https://<railway-backend>/api/analysis/operations
```

The response must show `execution_mode=worker`, at least one `healthy_worker_count`, and a recent worker `last_seen_at`. During long parsing operations, `analysis_jobs.last_heartbeat_at` must keep advancing. Do not expose this staff endpoint through Vercel or public status pages.

## 4. Vercel frontend

Create or update the Vercel project for the public site and workspace.

Required Vercel settings:

```text
Root Directory = frontend
Build Command = npm run build
Output Directory = .
```

The frontend project must include:

```text
frontend/assets/
frontend/workspace/
frontend/vercel.json
frontend/index.html
frontend/js/devbareun-api.js
frontend/member-dashboard-app/package-lock.json
```

Build locally before deploy:

```bash
cd frontend/member-dashboard-app
npm ci
cd ..
npm run build
cd ..
python tools/check_frontend_assets.py --root .
python tools/check_frontend_deploy_surface.py --root . --strict
```

Frontend env values are public only. Vercel may receive `VITE_API_BASE_URL`, `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`; it must not receive backend secrets.

## 5. Lemon Squeezy

Configure Lemon Squeezy with the production backend webhook URL:

```text
https://<railway-backend-domain>/api/billing/webhook
```

Backend env must include:

```text
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=<backend only>
LEMON_SQUEEZY_STORE_ID=<store id>
LEMON_SQUEEZY_WEBHOOK_SECRET=<backend only>
LEMON_SQUEEZY_SINGLE_VARIANT_ID=<variant id>
LEMON_SQUEEZY_PLUS_VARIANT_ID=<variant id>
LEMON_SQUEEZY_PRO_VARIANT_ID=<variant id>
```

Webhook signature validation is fail-closed in production; do not enable mock payment in production.

## 6. Production env validation

Before deploying real provider values, create local copies of the production env files and validate them:

```bash
python tools/validate_production_env.py \
  --backend-env backend/.env.production \
  --frontend-env frontend/.env.production
```

Expected: zero errors. Placeholder warnings are only acceptable when validating `.env.example` with `--allow-placeholders`.

## 6A. Provider configuration preflight

Before configuring the provider dashboards, use the safe templates in:

```text
deploy/env/railway-web.env.template
deploy/env/railway-worker.env.template
deploy/env/vercel.env.template
```

Use real exported values from secure local files to detect Railway web/worker/Vercel drift without printing secrets:

```bash
python tools/check_provider_config.py \
  --railway-web-env /secure/path/railway-web.env \
  --railway-worker-env /secure/path/railway-worker.env \
  --vercel-env /secure/path/vercel.env
```

The Railway worker must match the Railway web service for shared Supabase, Redis, Lemon Squeezy, origin and production-security configuration. Vercel must match the public site/API/Supabase browser values and must not contain backend-only secrets. Details: `docs/PRODUCTION_CONFIG_PREFLIGHT_V1415.md`.

For CI/template validation only, placeholders are allowed:

```bash
python tools/check_provider_config.py \
  --railway-web-env deploy/env/railway-web.env.template \
  --railway-worker-env deploy/env/railway-worker.env.template \
  --vercel-env deploy/env/vercel.env.template \
  --allow-placeholders
```


## 6E. Company team foundation

After applying `2026_06_21_v1432_company_team_foundation.sql`, the Workspace **Team** page can create a company roster and manual invitation URLs. Keep the default backend policy:

```text
DEVBAREUN_TEAM_INVITE_TTL_HOURS=72
```

The v1.4.32 invite workflow stores only token hashes. Send the one-time URL through an approved channel and do not treat company membership as project sharing; project/file/report access remains unchanged until a later project-access migration.

Run the static guard before release:

```bash
python tools/check_company_team_foundation.py --root .
```

## 7. Deploy order

Use this order to avoid broken frontend/API interactions:

1. Supabase migrations and private buckets.
2. Railway backend web service with production env.
3. Railway analysis worker service with production env.
4. Railway audit archive worker service with production env.
5. Vercel frontend with public env.
6. Lemon Squeezy webhook test event.
7. Deployed smoke test.

## 8. Smoke test

After all services are deployed, run:

```bash
python tools/smoke_deploy.py \
  --frontend-url https://devbareun.com \
  --backend-url https://devbareun-production.up.railway.app \
  --strict \
  --retries 3
```

The smoke test checks the public frontend, workspace shell, backend health, backend readiness, backend version and CSRF initializer.

Production readiness should report:

```text
production_security = enabled
csrf_token = required
analysis_job_mode = worker
rate_limit = upstash
supabase_private = configured
lemonsqueezy = configured
docs = disabled
legacy_project_routes = disabled
```

## 9. Post-deploy functional checks

Run these manually after smoke test:

1. Open `https://devbareun.com/` and verify logo/favicon/Open Graph assets load.
2. Open `https://devbareun.com/workspace/` and verify the React shell loads.
3. Register or log in with a Supabase Auth account.
4. Create a project.
5. Upload a small safe `.xlsx` file.
6. Start analysis and verify a queued job appears in `analysis_jobs`.
7. Confirm the Railway worker completes the job and writes `analysis_results`.
8. Confirm result dashboard renders KPI/data-quality/risk panels without raw JSON as the primary view.
9. Generate or download a report if the plan allows it.
10. Test Lemon Squeezy checkout in the configured mode.

## 9A. Guarded pilot acceptance

After the public smoke test passes, run the authenticated pilot acceptance tool using a dedicated customer test account. The default command is read-only. Do not run write, analysis or report flags without the explicit confirmation values; analysis may consume a credit.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

For a controlled upload/analysis/report flow, follow `docs/PILOT_ACCEPTANCE_V1427.md`. Keep evidence outside the repository and never place pilot credentials in Vercel, Railway templates, `.env` files or CI logs.

## 10. Rollback

Rollback must preserve user data. Do not delete Supabase tables or buckets during rollback.

Safe rollback order:

1. Disable Vercel deployment or roll back to previous frontend deployment.
2. Set Railway web service to previous image/package.
3. Stop Railway worker service if it is producing repeated failed jobs.
4. Keep Supabase migrations in place; additive bridge migrations are intended to be backward-compatible.
5. If a new endpoint is failing, disable traffic at frontend/API route level rather than deleting data.
6. Re-run smoke test against the restored deployment.

Rollback smoke test:

```bash
python tools/smoke_deploy.py \
  --frontend-url https://devbareun.com \
  --backend-url https://devbareun-production.up.railway.app \
  --retries 3
```

## 11. Release sign-off

A production release is signable only when all of these are true:

```text
Database contract passed
Deployment runbook check passed
Release gate passed
API contract passed
Backend tests passed
Frontend build passed
Frontend deploy surface passed
Production env validator passed with real env files
Provider configuration preflight passed with real provider exports
Deployed smoke test passed
Pilot acceptance read-only check passed
```


## Failed-job recovery

Do not bulk-rerun failed worker jobs. After confirming worker health and Railway logs, staff may inspect `GET /api/analysis/operations/recovery-jobs` and requeue a single reviewed job through `POST /api/analysis/operations/jobs/{job_id}/retry`. A `dead_lettered` job requires `{ "reset_attempts": true }`; a job with a saved result must not be retried.

## v1.4.18 integrity prerequisite

Apply `2026_06_19_v1418_analysis_idempotency.sql` after v1.4.17 and before deploying the backend. The Railway web and worker services require the same Supabase service-role configuration because the worker calls the atomic `consume_analysis_usage_once` RPC.


## v1.4.19 report snapshot integrity

After applying `2026_06_19_v1419_report_snapshot_integrity.sql`, generate one PDF and one Excel report from a completed project. Confirm the archive list reports `snapshot_available: true`, then download each report. The backend-only `record_report_download` RPC increments download telemetry; do not expose this RPC to the frontend.

```bash
python tools/check_report_snapshot.py --root .
```

## v1.4.20 upload checksum integrity

Apply `2026_06_19_v1420_upload_checksum_integrity.sql` after v1.4.19 and before deploying the backend. Set `DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM=true` on both Railway web and worker services. Upload a small supported test file through the workspace, start an analysis, and confirm its uploaded file metadata changes from `pending_verification` to `verified`. A `mismatch` must fail the job before result creation or credit consumption.

```bash
python tools/check_upload_checksum_integrity.py --root .
```


## v1.4.21 upload security screening and quarantine

Apply `2026_06_19_v1421_upload_security_screening.sql` after v1.4.20 before deploying the web and worker services. Set the same values for the office archive limits and macro/PDF blocking policy on both Railway services.

Run one harmless `.xlsx` and one PDF through the workspace after deploy. Confirm the file metadata changes from `security_scan_status=pending` to `clean`, `quarantine_status=released`, then confirm parser execution continues. For a blocked source, verify the file becomes `upload_status=quarantined`, no result is created, and no credit is consumed. This gate is deterministic admission screening, not a replacement for a provider-managed malware scanner.


## v1.4.22 analysis input provenance

Apply `2026_06_19_v1422_analysis_input_provenance.sql` after v1.4.21 before deploying both Railway services. Start one analysis from a supported test upload and confirm the completed `analysis_results` row includes `input_manifest`, `input_manifest_sha256` and `input_file_count`. Open the workspace result and verify **Analysis source traceability** lists files without exposing a Supabase storage path or signed URL.

```bash
python tools/check_analysis_provenance.py --root .
```


## v1.4.23 panel access verification

After applying `2026_06_20_v1423_panel_access_boundaries.sql`, verify role boundaries with real non-owner test accounts. Support/finance must receive `403` for customer project/report/upload resources outside their permitted modules; only owner/operator can call `/api/analysis/operations`. Staff status changes must use the owner-only staff endpoint.


## v1.4.24 audit integrity verification

After applying `2026_06_20_v1424_audit_integrity.sql`, deploy the Railway web service and verify the owner-only audit endpoint. New events are append-only and are written through a database RPC.

```bash
curl -fsS -H "Authorization: Bearer <OWNER_ACCESS_TOKEN>" \
  "$BACKEND_URL/api/super-admin/audit-integrity?limit=2000"
```

Treat `verified=false` as an operational incident. Preserve the returned audit ID and `X-Request-ID`; do not repair audit rows with direct update/delete SQL.


## 9A. External audit archive worker

After applying `2026_06_20_v1425_audit_archive_outbox.sql`, create a third Railway service:

```text
Root Directory = backend
Config file = backend/railway.audit-archive.json
Start Command = python -m app.audit_archive_worker --loop --interval 15 --batch-size 25
```

Copy the Railway audit archive template `deploy/env/railway-audit-archive.env.template` and provide a backend-only archive receiver:

```bash
python tools/check_provider_config.py \
  --railway-web-env /secure/railway-web.env \
  --railway-worker-env /secure/railway-worker.env \
  --railway-audit-archive-env /secure/railway-audit-archive.env \
  --vercel-env /secure/vercel.env
```

Set `DEVBAREUN_AUDIT_ARCHIVE_MODE=webhook`, a HTTPS `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL`, and `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET` on Railway only. Verify a test audit event reaches the archive receiver and that its HMAC and `audit_id` deduplication checks pass. Then open `GET /api/super-admin/audit-archive` as an owner; it should show an online archive worker and increasing delivered count.

Rollback: set `DEVBAREUN_AUDIT_ARCHIVE_MODE=disabled` on the archive worker and restart it. The database outbox remains intact; no audit chain rows are deleted. Do not remove the v1.4.25 migration during rollback.

## v1.4.26 operational health verification

After web, analysis-worker and audit-archive worker services are running, sign in as an `owner` or `operator` and open **Super Admin → Operations health**.

Expected state after a quiet startup:

```text
overall status: healthy
runtime component: healthy
analysis component: healthy with at least one healthy worker when worker mode is enabled
audit archive: healthy when webhook mode is enabled; disabled only when archive delivery is deliberately not in scope
```

For `degraded` or `unavailable`, use the incident code to choose the correct existing recovery path. Do not retry failed jobs or archive events until the underlying store/provider condition is corrected.



## v1.4.28 error telemetry verification

Configure privacy-safe error telemetry on Railway web, analysis worker and audit archive worker before the deploy. Sentry receives only sanitized synthetic error events; do not add `DEVBAREUN_SENTRY_DSN` to Vercel.

```bash
python tools/check_error_telemetry.py --root .
```

Set `DEVBAREUN_ERROR_TELEMETRY_MODE=sentry`, `DEVBAREUN_REQUIRE_ERROR_TELEMETRY=true`, and a real `DEVBAREUN_SENTRY_DSN` on all Railway services. After deployment, verify `/api/readiness` reports external error telemetry configured and correlate a safe request using the `X-Request-ID` response header in Railway logs.


## Backup and disaster-recovery checkpoint

Before production sign-off, set the backup policy keys on each Railway service:

```text
DEVBAREUN_BACKUP_REQUIRED=true
DEVBAREUN_BACKUP_RPO_HOURS=24
DEVBAREUN_BACKUP_RTO_HOURS=8
DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS=90
DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED=true
```

Create a secured, untracked backup operator configuration from
`deploy/env/backup-operator.env.template`. It contains the direct database
backup connection and must not be copied to Vercel or Railway application
services. Before go-live, complete one isolated restore preflight and record
the actual recovery time. See `docs/BACKUP_AND_RECOVERY_V1429.md`.

## v1.4.30 privacy and retention workflow

After applying `2026_06_21_v1430_data_lifecycle_requests.sql`, set the four
`DEVBAREUN_*` data lifecycle policy variables on each Railway service and run:

```bash
python tools/check_data_lifecycle.py --root .
```

Create one pilot export request and one erasure request using a test customer,
then verify an owner can review them. Do not enable an automatic physical purge
unless a separately approved operator, legal retention review and restore drill
are complete.

Set this exact baseline on Railway web, analysis worker and audit archive worker:

```text
DEVBAREUN_SOFT_DELETE_RETENTION_DAYS=30
DEVBAREUN_ERASURE_GRACE_DAYS=14
DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS=7
DEVBAREUN_AUTO_PURGE_ENABLED=false
```


## v1.4.31 billing lifecycle

Set `DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS=5` on Railway web, analysis worker and audit archive worker. Apply `2026_06_21_v1431_billing_lifecycle_integrity.sql` after v1.4.30, then verify an authenticated `GET /api/billing/checkouts/{checkout_id}` result after a Lemon Squeezy test checkout. Keep `LEMON_SQUEEZY_WEBHOOK_SECRET` backend-only.

## v1.4.33 Project Sharing

Apply `2026_06_21_v1433_project_sharing.sql` after the company-team migration. Company membership remains insufficient for project data access. Use the Workspace **Project Access** screen to grant `viewer`, `editor`, or `manager` access to active members.

```bash
python tools/check_project_sharing.py --root .
```


## v1.4.34 project activity timeline

Apply `2026_06_21_v1434_project_activity_timeline.sql` after `2026_06_21_v1433_project_sharing.sql` before deploying the updated web API and analysis worker. The worker emits analysis completion/failure timeline events; no additional environment variable is required.
