# Environment Variables

This file is the live deployment reference for DevBareun.

## Backend: Railway

Set these in the Railway backend service. Values with secrets must never be committed.

```env
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_VERSION=1.4.0-production-saas-core
PUBLIC_SITE_URL=https://devbareun.com
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,https://devbareun.vercel.app
DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,https://devbareun.vercel.app

DEVBAREUN_MAX_FILES=12
DEVBAREUN_MAX_FILE_MB=30
DEVBAREUN_MAX_TOTAL_MB=120
DEVBAREUN_MAX_UPLOAD_BYTES=104857600

DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false

DEVBAREUN_ADMIN_EMAILS=admin@devbareun.com
DEVBAREUN_ALLOW_ADMIN_EMAIL_FALLBACK=false
DEVBAREUN_ALLOW_DEVBAREUN_DOMAIN_ADMINS=false

DEVBAREUN_RATE_LIMIT_ENABLED=true
DEVBAREUN_RATE_LIMIT_WINDOW_SECONDS=60
DEVBAREUN_RATE_LIMIT_DEFAULT_PER_MIN=180
DEVBAREUN_RATE_LIMIT_AUTH_PER_MIN=20
DEVBAREUN_RATE_LIMIT_UPLOAD_PER_MIN=30
DEVBAREUN_RATE_LIMIT_ANALYSIS_PER_MIN=20
DEVBAREUN_RATE_LIMIT_EXPORT_PER_MIN=60
DEVBAREUN_RATE_LIMIT_ADMIN_PER_MIN=120
DEVBAREUN_RATE_LIMIT_WEBHOOK_PER_MIN=100

DEVBAREUN_GUEST_RESULT_DAYS=7
DEVBAREUN_GUEST_RESULT_MAX_DAYS=7

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=replace_with_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=replace_with_service_role_key_backend_only
SUPABASE_JWT_SECRET=replace_with_supabase_jwt_secret_if_using_local_jwt_verification
SUPABASE_STORAGE_BUCKET=project-files

FRONTEND_SUCCESS_URL=https://devbareun.com/result-dashboard.html?payment=success&project_id={project_id}&session_id={CHECKOUT_SESSION_ID}
FRONTEND_CANCEL_URL=https://devbareun.com/?payment=cancelled&project_id={project_id}

DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_SINGLE_VARIANT_ID=
LEMON_SQUEEZY_PLUS_VARIANT_ID=
LEMON_SQUEEZY_PRO_VARIANT_ID=

OPENAI_MAPPING_ENABLED=false
OPENAI_MAPPING_MODEL=gpt-4.1-mini
OPENAI_MAPPING_CONFIDENCE_THRESHOLD=85
OPENAI_API_KEY=
```

## Frontend: Vercel

Set Vercel Root Directory to `frontend`.

The current frontend is static HTML, so public env variables are mainly a deployment checklist and future build reference. Keep secrets out of Vercel frontend variables.

```env
VITE_DEVBAREUN_API_BASE_URL=https://devbareun-production.up.railway.app
VITE_DEVBAREUN_API_BASE=https://devbareun-production.up.railway.app
VITE_PUBLIC_SITE_URL=https://devbareun.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=replace_with_supabase_anon_key
```

## Secret Boundary

- Backend only: `SUPABASE_SERVICE_ROLE_KEY`, `LEMON_SQUEEZY_API_KEY`, `LEMON_SQUEEZY_WEBHOOK_SECRET`, and `OPENAI_API_KEY`.
- Frontend allowed: Supabase anon key, public site URL, public API URL. Lemon Squeezy API and webhook secrets stay backend-only.
- Production must keep `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
