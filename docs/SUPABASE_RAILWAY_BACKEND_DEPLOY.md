# DevBareun Supabase + Railway Backend Deploy

This guide prepares the production backend first. Keep secrets in Railway/Supabase dashboards or local environment variables only.

## 1. Supabase

Create a Supabase project, then collect:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- Postgres connection string for `SUPABASE_DB_URL`

Run the migrations from the repository root:

```powershell
$env:SUPABASE_DB_URL="postgresql://..."
.\tools\deploy_supabase_v140.ps1
```

Migration order:

1. `database\2026_05_29_v140_production_saas_core.sql`
2. `database\2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `database\seed_plans.sql`

The production storage bucket is:

```text
project-files
```

It must stay private.

## 2. Railway Backend

Create a Railway project and backend service. Add the variables from `backend\.env.example` in Railway.

Minimum required production variables:

```text
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_VERSION=1.4.0-production-saas-core
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com
DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_DISABLE_DOCS=true
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=project-files
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=396148
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_SINGLE_VARIANT_ID=1741208
LEMON_SQUEEZY_PLUS_VARIANT_ID=1741246
LEMON_SQUEEZY_PRO_VARIANT_ID=1741254
```

Deploy from the repository root:

```powershell
$env:RAILWAY_TOKEN="..."
$env:RAILWAY_PROJECT_ID="..."
$env:RAILWAY_SERVICE="..."
$env:RAILWAY_ENVIRONMENT="production"
.\tools\deploy_railway_backend.ps1
```

If the backend service is already linked locally, `RAILWAY_PROJECT_ID` and `RAILWAY_SERVICE` can be omitted.

## 3. Health Check

After Railway gives a public backend URL:

```powershell
.\tools\check_backend_health.ps1 -BaseUrl "https://your-backend.up.railway.app"
```

Expected health response includes:

```json
{
  "status": "ok",
  "service": "DevBareun Backend",
  "version": "1.4.0"
}
```

## 4. Frontend Link Later

After backend health is stable, set the frontend environment:

```text
VITE_API_BASE_URL=https://your-backend.up.railway.app
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

Do not put `SUPABASE_SERVICE_ROLE_KEY` in frontend/Vercel variables.
