# DevBareun v1.4.15 Production Configuration Preflight

Production configuration is split across three providers. The common failure mode is not a missing key; it is **configuration drift**: Railway web, Railway worker and Vercel point to different public domains, API domains or Supabase projects.

This release adds placeholder-only templates and a local preflight checker. The checker never calls a provider and never prints secret values.

## 1. Provider templates

Tracked safe templates:

```text
deploy/env/railway-web.env.template
deploy/env/railway-worker.env.template
deploy/env/vercel.env.template
```

They are references only. Put real values in Railway/Vercel provider dashboards, not in this repository.

## 2. Railway web service

Use `deploy/env/railway-web.env.template` as the copy/paste source for the Railway web service.

Required service setup:

```text
Root Directory = backend
Start Command = python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 3. Railway analysis worker

Use `deploy/env/railway-worker.env.template`. The worker must have the same protected Supabase, Redis and Lemon Squeezy values as the web service.

Required service setup:

```text
Root Directory = backend
Start Command = python -m app.analysis_worker --loop --interval ${DEVBAREUN_ANALYSIS_WORKER_INTERVAL:-10} --batch-size ${DEVBAREUN_ANALYSIS_WORKER_BATCH_SIZE:-1}
DEVBAREUN_ANALYSIS_JOB_MODE=worker
```

## 4. Vercel frontend

Use `deploy/env/vercel.env.template` for Vercel public values.

```text
Root Directory = frontend
Build Command = npm run build
Output Directory = .
```

Only browser-safe public values belong in Vercel. Never copy these Railway-only values to Vercel:

```text
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
LEMON_SQUEEZY_API_KEY
LEMON_SQUEEZY_WEBHOOK_SECRET
UPSTASH_REDIS_REST_TOKEN
DATABASE_URL
```

## 5. Validate real exports before deploy

Export or make temporary local copies of the three provider environments outside the repository, then run:

```bash
python tools/check_provider_config.py \
  --railway-web-env /secure/path/railway-web.env \
  --railway-worker-env /secure/path/railway-worker.env \
  --vercel-env /secure/path/vercel.env
```

The checker validates both provider-specific correctness and shared configuration:

```text
Railway production security flags
Railway web/worker shared private config
Worker mode
Public site URL alignment
Railway API URL / Vercel API URL alignment
Supabase public URL + anon key alignment
Vercel backend-secret exclusion
```

A non-zero exit code means do not deploy until the drift is fixed.

## 6. Template/CI check

The committed templates intentionally have placeholders. Validate their shape with:

```bash
python tools/check_provider_config.py \
  --railway-web-env deploy/env/railway-web.env.template \
  --railway-worker-env deploy/env/railway-worker.env.template \
  --vercel-env deploy/env/vercel.env.template \
  --allow-placeholders
```

Run this with the broader local gates before production deployment:

```bash
python tools/validate_production_env.py \
  --backend-env /secure/path/railway-web.env \
  --frontend-env /secure/path/vercel.env
python tools/check_provider_config.py \
  --railway-web-env /secure/path/railway-web.env \
  --railway-worker-env /secure/path/railway-worker.env \
  --vercel-env /secure/path/vercel.env
python tools/release_gate.py --root .
python tools/check_database_contract.py --root .
python tools/check_deploy_runbook.py --root .
```

Then follow `docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md` for Supabase migrations, Railway deployment, Vercel deployment, Lemon Squeezy webhook verification, smoke testing and rollback.


## v1.4.16 worker liveness settings

```text
DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS=60
DEVBAREUN_ANALYSIS_WORKER_STATUS_STALE_SECONDS=90
```

Set these only on Railway backend services. They are not Vercel/frontend values.


Worker retry budget is also checked for Railway web/worker parity: `DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS` must be an integer from 1 to 10.

## v1.4.20 upload checksum setting

Set `DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM=true` in both Railway service configurations. Keep it out of Vercel because the browser does not need this backend policy flag. The provider parity checker verifies that web and worker agree.


## v1.4.21 upload security screening parity

Set the five screening values below identically in Railway web and Railway worker exports before validation:

```text
DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES=2000
DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES=251658240
DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO=500
DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS=false
DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT=false
```

The provider parity checker compares the values but never prints secret values. These controls provide deterministic parser-admission screening; they do not claim to provide antivirus scanning.


## v1.4.25 audit archive worker parity

Use `deploy/env/railway-audit-archive.env.template` for the third Railway service. Pass it to `tools/check_provider_config.py` with `--railway-audit-archive-env`. The checker requires the audit archive service to match Railway web on Supabase, rate-limit, origin and archive configuration, and requires `DEVBAREUN_AUDIT_ARCHIVE_MODE=webhook` for that service.


## v1.4.28 error telemetry parity

`tools/check_provider_config.py` verifies `DEVBAREUN_ERROR_TELEMETRY_MODE`, `DEVBAREUN_REQUIRE_ERROR_TELEMETRY`, `DEVBAREUN_SENTRY_DSN`, and `DEVBAREUN_REQUEST_LOGS_ENABLED` are identical across Railway web, analysis worker and audit archive worker. The DSN is backend-only and must not be exported to Vercel.


## v1.4.31 billing webhook parity

`DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS` must match across Railway web, analysis worker and audit archive worker. It is backend-only and must not be sent to Vercel.
