# Deployment

DevBareun has separate deploy roots.

## Frontend: Vercel

- Root Directory: `frontend`
- Public domain: `https://devbareun.com`
- Static files only: HTML, CSS, JS, assets.
- Never add backend secrets to Vercel.

Recommended public variables:

```env
VITE_PUBLIC_SITE_URL=https://devbareun.com
VITE_API_BASE_URL=https://devbareun-production.up.railway.app
VITE_API_URL=https://devbareun-production.up.railway.app
VITE_DEVBAREUN_API_BASE_URL=https://devbareun-production.up.railway.app
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=replace_with_supabase_anon_key
```

## Backend: Railway

- Root Directory: `backend`
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Private secrets live here only.

Required production settings:

```env
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com
CORS_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=replace_with_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=backend_only_service_role_key
SUPABASE_STORAGE_BUCKET=project-files
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=backend_only_api_key
LEMON_SQUEEZY_WEBHOOK_SECRET=backend_only_webhook_secret
```

## Supabase

Apply SQL in `database/SUPABASE_DEPLOY_ORDER.md`. New users default to `customer`. Promote the first owner manually:

```sql
update public.users_profile
set role = 'owner', status = 'active'
where lower(email) = lower('info@devbareun.com');
```

The same command is also available as `database/promote_owner_info_devbareun.sql`.

## Production Checks

- `GET /api/health`
- `GET /api/saas/health`
- `GET /api/version`
- Confirm health shows database and storage configured before real uploads.

## Clean Release Package

Use the release packager instead of manually zipping the repository:

```powershell
.\tools\package_release.ps1 -OutputDir dist -Name devbareun-production
```

The package excludes `.git`, `.venv`, caches, `.env` files, local storage, logs and temporary data. If a forbidden file is detected, the script fails before creating the ZIP.
