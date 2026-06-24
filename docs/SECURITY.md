# Security

## Auth Flow

Customers and staff authenticate with Supabase Auth. The frontend stores the browser session, but every protected API call is revalidated by the backend using the bearer token or auth cookie.

`/api/auth/pilot-login` is local-only and must require:

```env
DEVBAREUN_ENABLE_PILOT_LOGIN=true
DEVBAREUN_PRODUCTION_SECURITY=false
```

Production must keep pilot login disabled.

## Role Authorization

Super Admin routes require one of:

- `owner`
- `support`
- `analyst`
- `finance`
- `operator`

Critical operations such as staff management and role changes are owner-only. Unauthorized requests must return 403.

## Secret Boundary

Backend-only secrets:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`
- `OPENAI_API_KEY`

Frontend may use only public Supabase anon and public API URL values.

## Upload Safety

Backend upload metadata validation must check file type, size, sanitized names and path traversal. Railway ephemeral storage is not a production storage layer; production uploads must use Supabase Storage or another durable private object store.

## Rate Limiting

Rate limits cover auth, upload, analysis, export, webhook, billing and admin paths. Production must use Upstash Redis or an explicitly approved temporary in-memory override. With `DEVBAREUN_PRODUCTION_SECURITY=true` and `DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false`, missing Redis fails closed with `rate_limiter_not_configured`.

## Audit Logs

Admin actions should write audit logs for staff creation, role/status changes, credit/payment updates, support notes and report deletion.
