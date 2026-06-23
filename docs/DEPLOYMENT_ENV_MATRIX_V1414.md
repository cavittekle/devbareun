# DevBareun v1.4.14 Deployment Environment Matrix

Use this matrix to keep backend-only secrets out of the browser and to keep Railway web/worker services aligned.

Provider-specific placeholder templates are in `deploy/env/railway-web.env.template`, `deploy/env/railway-worker.env.template` and `deploy/env/vercel.env.template`. Validate real exports with `python tools/check_provider_config.py`.

| Key | Scope | Required | Notes |
|---|---|---:|---|
| `DEVBAREUN_ENV` | Railway web + worker | Yes | Must be `production`. |
| `APP_ENV` | Railway web + worker | Yes | Must be `production`. |
| `DEVBAREUN_PRODUCTION_SECURITY` | Railway web + worker | Yes | Must be `true`. |
| `DEVBAREUN_REQUIRE_CSRF_TOKEN` | Railway web + worker | Yes | Must be `true`. |
| `DEVBAREUN_ANALYSIS_JOB_MODE` | Railway web + worker | Yes | Must be `worker`. |
| `PUBLIC_SITE_URL` | Railway web + worker | Yes | `https://devbareun.com`. |
| `DEVBAREUN_ALLOWED_ORIGINS` | Railway web + worker | Yes | HTTPS origins only. |
| `FRONTEND_PUBLIC_API_BASE_URL` | Railway web + worker | Yes | Railway backend base URL. |
| `SUPABASE_URL` | Railway web + worker, Vercel public | Yes | Public project URL. |
| `SUPABASE_ANON_KEY` | Railway web + worker, Vercel public | Yes | Browser-safe anon key. |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Yes | Railway only; never Vercel. |
| `SUPABASE_JWT_SECRET` | Backend only | Optional | Railway only if JWT validation needs it. |
| `SUPABASE_STORAGE_BUCKET` | Railway web + worker | Yes | `project-files`. |
| `SUPABASE_REPORTS_BUCKET` | Railway web + worker | Yes | `reports`. |
| `DEVBAREUN_PAYMENT_PROVIDER` | Railway web + worker | Yes | `lemonsqueezy`. |
| `LEMON_SQUEEZY_API_KEY` | Backend only | Yes | Railway only; never Vercel. |
| `LEMON_SQUEEZY_STORE_ID` | Railway web + worker | Yes | Store id. |
| `LEMON_SQUEEZY_WEBHOOK_SECRET` | Backend only | Yes | Railway only; never Vercel. |
| `LEMON_SQUEEZY_SINGLE_VARIANT_ID` | Railway web + worker | Yes | Single analysis plan. |
| `LEMON_SQUEEZY_PLUS_VARIANT_ID` | Railway web + worker | Yes | Plus plan. |
| `LEMON_SQUEEZY_PRO_VARIANT_ID` | Railway web + worker | Yes | Pro plan. |
| `UPSTASH_REDIS_REST_URL` | Railway web + worker | Yes | Production rate limit backend. |
| `UPSTASH_REDIS_REST_TOKEN` | Backend only | Yes | Railway only; never Vercel. |
| `VITE_PUBLIC_SITE_URL` | Vercel public | Yes | Browser-exposed. |
| `VITE_API_BASE_URL` | Vercel public | Yes | Railway backend base URL. |
| `VITE_API_URL` | Vercel public | Optional | Alias for frontend compatibility. |
| `VITE_DEVBAREUN_API_BASE_URL` | Vercel public | Optional | Alias for frontend compatibility. |
| `VITE_SUPABASE_URL` | Vercel public | Yes | Browser-exposed Supabase URL. |
| `VITE_SUPABASE_ANON_KEY` | Vercel public | Yes | Browser-safe anon key only. |
| `DATABASE_URL` | Backend only | No | Do not use unless a future backend path requires direct Postgres. |

## Frontend forbidden keys

These keys are backend-only and must not appear in Vercel/frontend env values:

| Key | Scope | Reason |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Bypasses RLS. |
| `SUPABASE_JWT_SECRET` | Backend only | Token verification secret. |
| `LEMON_SQUEEZY_API_KEY` | Backend only | Payment provider private API key. |
| `LEMON_SQUEEZY_WEBHOOK_SECRET` | Backend only | Webhook signature secret. |
| `UPSTASH_REDIS_REST_TOKEN` | Backend only | Rate-limit datastore token. |
| `DATABASE_URL` | Backend only | Database credential. |

## Provider mapping

| Provider | Root / service | Receives |
|---|---|---|
| Supabase | SQL Editor + Storage | Migrations, private `project-files` and `reports` buckets. |
| Railway web service | `Root Directory = backend` | Backend env matrix, web start command. |
| Railway worker service | `Root Directory = backend` | Same backend env matrix, analysis-worker start command. |
| Railway audit archive worker | `Root Directory = backend` | Same backend env matrix plus audit archive webhook configuration; starts `app.audit_archive_worker`. |
| Vercel | `Root Directory = frontend` | Public Vite/browser values only. |
| Lemon Squeezy | Store/webhook settings | Backend webhook URL and variant IDs. |


## v1.4.16 worker liveness settings

```text
DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS=60
DEVBAREUN_ANALYSIS_WORKER_STATUS_STALE_SECONDS=90
```

Set these only on Railway backend services. They are not Vercel/frontend values.

| `DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS` | Railway web + Railway worker | Integer 1–10; default `3`; both services must match. |

## v1.4.18 integrity prerequisite

Apply `2026_06_19_v1418_analysis_idempotency.sql` after v1.4.17 and before deploying the backend. The Railway web and worker services require the same Supabase service-role configuration because the worker calls the atomic `consume_analysis_usage_once` RPC.

## v1.4.20 upload checksum setting

| `DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM` | Railway web + Railway worker | Yes | Set `true`; both services must match. New browser uploads carry SHA-256 and the worker verifies storage bytes before parser execution. |


## v1.4.21 upload security screening settings

| Variable | Scope | Required | Notes |
|---|---|---:|---|
| `DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES` | Railway web + Railway worker | Yes | Same value in both services; caps OOXML archive entry count. |
| `DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES` | Railway web + Railway worker | Yes | Same value in both services; caps extracted OOXML size before parser use. |
| `DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO` | Railway web + Railway worker | Yes | Same value in both services; blocks suspiciously compressed OOXML archives. |
| `DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS` | Railway web + Railway worker | Yes | Policy flag. `false` records macro presence as a finding; `true` quarantines XLSM macro workbooks. |
| `DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT` | Railway web + Railway worker | Yes | Policy flag. `false` records selected PDF active-content markers; `true` quarantines them. |

Do not put these backend policy flags in Vercel.


## Audit correlation

`X-Request-ID` is generated by the backend and carried into v1.4.24 audit events. No new provider environment variable is required. Do not add request identifiers, bearer tokens or raw request payloads to frontend analytics/configuration values.


## v1.4.25 external audit archive settings

| Key | Scope | Required | Notes |
|---|---|---:|---|
| `DEVBAREUN_AUDIT_ARCHIVE_MODE` | Railway web + analysis worker + audit archive worker | Yes | `webhook` for external delivery; `disabled` keeps the outbox inside Supabase only. |
| `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL` | Backend only | Yes when mode is `webhook` | HTTPS archive receiver; never Vercel. |
| `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET` | Backend only | Yes when mode is `webhook` | HMAC secret; never Vercel. |
| `DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS` | Railway services | Yes | Integer `1–20`; keep equal across services. |
| `DEVBAREUN_AUDIT_ARCHIVE_BATCH_SIZE` | Railway services | Yes | Max events claimed per archive-worker poll. |
| `DEVBAREUN_AUDIT_ARCHIVE_LEASE_SECONDS` | Railway services | Yes | Delivery lease duration; keep equal across services. |
| `DEVBAREUN_AUDIT_ARCHIVE_TIMEOUT_SECONDS` | Railway services | Yes | Outbound webhook timeout; max 30 seconds. |

The audit archive endpoint and HMAC secret are backend-only values and must never appear in Vercel/frontend env exports.


## v1.4.28 error telemetry

| Key | Scope | Notes |
|---|---|---|
| `DEVBAREUN_ERROR_TELEMETRY_MODE` | Backend only | `sentry` in production; identical across Railway web and workers. |
| `DEVBAREUN_REQUIRE_ERROR_TELEMETRY` | Backend only | `true` blocks readiness when external telemetry is unavailable. |
| `DEVBAREUN_SENTRY_DSN` | Backend only | Railway only. Never place in Vercel. |
| `DEVBAREUN_REQUEST_LOGS_ENABLED` | Backend only | Emits privacy-safe structured request completion logs. |


## Backup operator (separate secure environment)

The backup operator is not a Railway or Vercel service. It has an untracked
configuration based on `deploy/env/backup-operator.env.template` and may hold
`DEVBAREUN_BACKUP_DATABASE_URL` plus the Supabase service-role key needed for
storage inventory. These values are forbidden in Vercel and should not be
added to Railway web, analysis worker or audit archive worker services.


### Backup policy keys on Railway services

| Variable | Scope | Notes |
|---|---|---|
| `DEVBAREUN_BACKUP_REQUIRED` | Backend only | Must be `true` in production. |
| `DEVBAREUN_BACKUP_RPO_HOURS` | Backend only | Initial target: `24`. |
| `DEVBAREUN_BACKUP_RTO_HOURS` | Backend only | Initial target: `8`. |
| `DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS` | Backend only | Initial target: `90`. |
| `DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED` | Backend only | Requires storage inventory confirmation. |

### Backup credential exclusion

| Variable | Scope | Notes |
|---|---|---|
| `DEVBAREUN_BACKUP_DATABASE_URL` | Backend only | Secure backup operator only; never Railway application services or Vercel. |
| `DEVBAREUN_BACKUP_OUTPUT_DIR` | Backend only | Secure backup operator only; must point outside repository storage. |

## v1.4.30 data lifecycle policy

Set these backend-only policy values identically on Railway web, analysis worker
and audit archive worker services. Do not expose them in Vercel:

```text
DEVBAREUN_SOFT_DELETE_RETENTION_DAYS=30
DEVBAREUN_ERASURE_GRACE_DAYS=14
DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS=7
DEVBAREUN_AUTO_PURGE_ENABLED=false
```

`DEVBAREUN_AUTO_PURGE_ENABLED` is not a browser setting. v1.4.30 does not ship
a physical purge worker; it only makes any future destructive policy explicit.

| Variable | Scope | Notes |
|---|---|---|
| `DEVBAREUN_SOFT_DELETE_RETENTION_DAYS` | Backend only | Identical on Railway web and workers; 7–365 days. |
| `DEVBAREUN_ERASURE_GRACE_DAYS` | Backend only | Identical on Railway web and workers; 1–90 days. |
| `DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS` | Backend only | Identical on Railway web and workers; 1–30 days. |
| `DEVBAREUN_AUTO_PURGE_ENABLED` | Backend only | Keep `false` until an independently reviewed physical purge operator exists. |


## v1.4.31 billing lifecycle

| Variable | Scope | Notes |
|---|---|---|
| `DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS` | Backend only | Set `5` identically on Railway web, analysis worker and audit archive worker. Allowed range: `1–20`; never expose it in Vercel. |

Apply `2026_06_21_v1431_billing_lifecycle_integrity.sql` after v1.4.30, then verify an authenticated `GET /api/billing/checkouts/{checkout_id}` result after a Lemon Squeezy test checkout. Keep `LEMON_SQUEEZY_WEBHOOK_SECRET` backend-only.

| `DEVBAREUN_TEAM_INVITE_TTL_HOURS` | Backend only | Manual company invitation expiry; 1–168 hours, default 72. Keep identical on Railway web and workers. |


## v1.4.34 project activity timeline

Apply `2026_06_21_v1434_project_activity_timeline.sql` after `2026_06_21_v1433_project_sharing.sql` before deploying the updated web API and analysis worker. The worker emits analysis completion/failure timeline events; no additional environment variable is required.
