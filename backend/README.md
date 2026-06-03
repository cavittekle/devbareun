# DevBareun Backend v1.4.0

FastAPI backend for DevBareun construction analytics, project control uploads, background project review jobs, executive dashboard APIs, billing, and report exports.

## Railway Start Command

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Railway config is stored in `railway.json` and uses `/api/health` as the healthcheck path.

## Required Production Environment

Copy values from `.env.example` into Railway. Keep these security flags set for production:

```text
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false
DEVBAREUN_DISABLE_DOCS=true
```

Supabase backend variables:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=project-files
```

Production checkout currently uses Lemon Squeezy:

```text
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_SINGLE_VARIANT_ID=
LEMON_SQUEEZY_PLUS_VARIANT_ID=
LEMON_SQUEEZY_PRO_VARIANT_ID=
```

Stripe variables may stay empty unless legacy Stripe checkout is enabled again.

## Health Checks

```text
GET /api/health
GET /api/saas/health
```

Expected backend health shape:

```json
{
  "status": "ok",
  "service": "DevBareun Backend",
  "database": "connected",
  "storage": "configured",
  "version": "1.4.0"
}
```

Without Supabase env values, `database` and `storage` show `not_configured`.

## Supabase Setup

Apply database SQL files from the repository root `database/` folder. For a clean v1.4.0 setup, use:

1. `2026_05_29_v140_production_saas_core.sql`
2. `2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `seed_plans.sql`

Then create a private Supabase Storage bucket named `project-files`.
