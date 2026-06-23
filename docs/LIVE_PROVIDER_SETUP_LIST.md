# DevBareun Live Provider Setup List

Use this only for live provider dashboards. Do not commit real secret values.

## Vercel

- Project Root Directory: `frontend`
- Build command: `npm run build`
- Output stays static under the `frontend` deploy.
- Domain: `devbareun.com`
- `www.devbareun.com` should redirect to `devbareun.com`.

Allowed public environment variables:

```text
VITE_PUBLIC_SITE_URL=https://devbareun.com
VITE_API_BASE_URL=https://devbareun-production.up.railway.app
VITE_API_URL=https://devbareun-production.up.railway.app
VITE_SUPABASE_URL=<supabase project url>
VITE_SUPABASE_ANON_KEY=<supabase anon key>
```

Do not add service role keys, JWT secrets, Lemon Squeezy API keys, webhook secrets, Redis tokens, or database passwords to Vercel.

## Railway

- Project Root Directory: `backend`
- Health check: `/api/health`
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Required production environment variables:

```text
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_AUTH_MODE=supabase
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com
DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com

DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=false
DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD=false
DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false
DEVBAREUN_DISABLE_DOCS=true

SUPABASE_URL=<supabase project url>
SUPABASE_ANON_KEY=<supabase anon key>
SUPABASE_SERVICE_ROLE_KEY=<backend only service role key>
SUPABASE_JWT_SECRET=<supabase jwt secret if required>
SUPABASE_STORAGE_BUCKET=project-files
SUPABASE_REPORTS_BUCKET=reports

DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=<live api key>
LEMON_SQUEEZY_STORE_ID=396148
LEMON_SQUEEZY_SINGLE_VARIANT_ID=1741208
LEMON_SQUEEZY_PLUS_VARIANT_ID=1741246
LEMON_SQUEEZY_PRO_VARIANT_ID=1741254
LEMON_SQUEEZY_WEBHOOK_SECRET=<live webhook signing secret>

UPSTASH_REDIS_REST_URL=<upstash redis rest url>
UPSTASH_REDIS_REST_TOKEN=<upstash redis rest token>
```

## Supabase

- Apply SQL files using `database/SUPABASE_DEPLOY_ORDER.md`.
- Run and review `database/production_rls_audit.sql`.
- Create private storage bucket `project-files`.
- Create private storage bucket `reports` if report archive files are stored.
- Create owner account for `info@devbareun.com`.
- Set the owner profile role/status in the database:

```text
role=owner
status=active
```

## Lemon Squeezy

- Store must be active for live payments.
- Webhook URL: `https://devbareun-production.up.railway.app/api/billing/webhook`
- Webhook signing secret must match `LEMON_SQUEEZY_WEBHOOK_SECRET` in Railway.
- Test live checkout for:
  - Single Project: `1741208`
  - Plus: `1741246`
  - Pro: `1741254`

## Live Verification

After deploy, verify:

```text
https://devbareun.com/
https://devbareun.com/workspace/
https://devbareun.com/workspace/?view=login
https://devbareun-production.up.railway.app/api/health
https://devbareun-production.up.railway.app/api/saas/health
```

Expected backend health:

```json
{
  "status": "ok",
  "database": "connected",
  "storage": "configured"
}
```

Run local checks against live URLs:

```powershell
.\tools\production_readiness_check.ps1 -FrontendUrl https://devbareun.com -BackendUrl https://devbareun-production.up.railway.app
.\tools\smoke_e2e.ps1 -FrontendBase https://devbareun.com -BackendBase https://devbareun-production.up.railway.app
```
