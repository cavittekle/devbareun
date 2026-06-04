# DevBareun Backend

FastAPI backend target for Railway.

## Deploy

- Railway Root Directory: `backend`
- Config file: `railway.json`
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Ignore rules: `.railwayignore`

## Local Run

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Required Production Environment

Copy values from `.env.example` into Railway. Keep these flags set for production:

```text
DEVBAREUN_ENV=production
APP_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_DEV_AUTH=false
DEVBAREUN_ENABLE_LOCAL_STORE=false
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ENABLE_PILOT_LOGIN=false
DEVBAREUN_ENABLE_PILOT_CHECKOUT=false
DEVBAREUN_DISABLE_DOCS=true
```

## Supabase

Backend-only variables:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=project-files
```

Expected live health after configuration:

```json
{
  "status": "ok",
  "database": "connected",
  "storage": "configured"
}
```

If `database` or `storage` returns `not_configured`, live Supabase setup is incomplete.

## Payment

Production checkout uses Lemon Squeezy:

```text
DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_SINGLE_VARIANT_ID=
LEMON_SQUEEZY_PLUS_VARIANT_ID=
LEMON_SQUEEZY_PRO_VARIANT_ID=
```

Webhook URL:

```text
https://devbareun-production.up.railway.app/api/billing/webhook
```

## Rate Limiting

Current rate limiting is in-memory and acceptable for one Railway instance. Before scaling to multiple instances, add Redis/Upstash-backed rate limiting.
