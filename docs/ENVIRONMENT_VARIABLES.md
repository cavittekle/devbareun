
# Environment Variables

## Backend

```env
APP_ENV=production
DEVBAREUN_VERSION=1.3.0-saas-foundation
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,https://devbareun.vercel.app
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_MAX_FILE_MB=30
DEVBAREUN_MAX_TOTAL_MB=120
DEVBAREUN_MAX_FILES=12

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=project-files

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_SINGLE_PRICE_ID=
STRIPE_PLUS_PRICE_ID=
STRIPE_PRO_PRICE_ID=

RESULT_LINK_DAYS=14
JWT_SECRET=
ADMIN_EMAILS=
```

## Frontend / Vercel

```env
VITE_API_URL=https://devbareun-production.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
```

## v1.3.2 Supabase Auth + Storage

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-backend-only
SUPABASE_STORAGE_BUCKET=devbareun-project-files
```

`SUPABASE_SERVICE_ROLE_KEY` must only exist in the backend environment. Do not add it to Vercel public frontend variables.
