# DevBareun v1.4.8 Production Readiness

This release adds a deploy-gate layer around the v1.4.x backend/frontend split. It does not replace provider setup in Supabase, Railway, Vercel, Lemon Squeezy or Upstash; it makes misconfiguration easier to detect before traffic reaches users.

## What changed

### Backend readiness endpoint

New public endpoint:

```text
GET /api/readiness
```

The response is secret-safe and contains:

```json
{
  "ready": false,
  "readiness": {
    "environment": "production",
    "production_security": true,
    "csrf_token": "required",
    "analysis_job_mode": "worker",
    "dev_auth": "disabled",
    "local_store": "disabled",
    "mock_payment": "disabled",
    "pilot_login": "disabled",
    "pilot_checkout": "disabled",
    "legacy_project_routes": "disabled",
    "ephemeral_upload": "disabled",
    "docs": "disabled",
    "supabase_private": "configured",
    "lemonsqueezy": "configured",
    "rate_limit": "upstash"
  },
  "errors": [],
  "warnings": []
}
```

`ready` is `false` when release-blocking production errors are present. Warnings are non-blocking but should be cleared before a public launch.

### Cross-platform env validator

New script:

```bash
python tools/validate_production_env.py \
  --backend-env backend/.env.production \
  --frontend-env frontend/.env.production
```

It verifies:

- backend production flags are fail-closed;
- Supabase, Lemon Squeezy and Upstash variables are present;
- `DEVBAREUN_ANALYSIS_JOB_MODE` is set and recommends `worker`;
- production origins are HTTPS and not wildcarded;
- frontend env does not contain backend-only secrets;
- frontend public URLs are HTTPS.

For checking committed examples without failing on placeholders:

```bash
python tools/validate_production_env.py \
  --backend-env backend/.env.example \
  --frontend-env frontend/.env.example \
  --allow-placeholders
```

### Cross-platform deployment smoke test

New script:

```bash
python tools/smoke_deploy.py \
  --frontend-url https://devbareun.com \
  --backend-url https://devbareun-production.up.railway.app \
  --strict \
  --retries 3
```

It checks:

- frontend `index.html`;
- frontend `/workspace/` route;
- backend `/api/health`;
- backend `/api/readiness`;
- backend `/api/version`;
- backend `/api/auth/csrf`.

`--strict` treats missing provider readiness, such as Upstash, Supabase private config or Lemon Squeezy config, as failures.

## Recommended production release order

1. Apply Supabase migrations in `database/SUPABASE_DEPLOY_ORDER.md`.
2. Verify storage buckets exist:
   - `project-files`
   - `reports`
3. Configure Railway backend env from `backend/.env.example`.
4. Set `DEVBAREUN_ANALYSIS_JOB_MODE=worker` on the Railway web service.
5. Add a second Railway worker service:

```bash
python -m app.analysis_worker --loop --interval 10 --batch-size 1
```

6. Configure Vercel frontend env from `frontend/.env.example`.
7. Run env validation locally or in CI.
8. Deploy backend web + worker.
9. Deploy frontend.
10. Run smoke test against live URLs.
11. Check `/api/readiness` shows no errors.

## Production env minimum

Backend must have, at minimum:

```text
DEVBAREUN_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_REQUIRE_CSRF_TOKEN=true
DEVBAREUN_DISABLE_DOCS=true
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=false
DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD=false
DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false
DEVBAREUN_ANALYSIS_JOB_MODE=worker
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
LEMON_SQUEEZY_API_KEY=...
LEMON_SQUEEZY_WEBHOOK_SECRET=...
```

Frontend must contain only public browser-safe values:

```text
VITE_PUBLIC_SITE_URL=https://devbareun.com
VITE_API_BASE_URL=https://devbareun-production.up.railway.app
VITE_SUPABASE_URL=https://...
VITE_SUPABASE_ANON_KEY=...
```

Never place these in frontend/Vercel env:

```text
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
LEMON_SQUEEZY_API_KEY
LEMON_SQUEEZY_WEBHOOK_SECRET
UPSTASH_REDIS_REST_TOKEN
DATABASE_URL
```

## Release tests added

`backend/tests/test_release_security.py` now also verifies:

- `/api/readiness` exists and exposes secret-safe release flags;
- readiness output includes CSRF and worker-mode status;
- cross-platform Python readiness tools are present;
- smoke tool checks `/api/readiness` and `/api/auth/csrf`.

Expected backend test result for this package:

```text
16 passed
```
