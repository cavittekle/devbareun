# DevBareun v1.3.9 — Production Security

This release hardens the v1.3.8 Admin Panel package for a real SaaS production path.

## Added security layers

- Supabase RLS migration for user/company/project/report ownership.
- Admin role protection with production-safe fallback behavior.
- Protected file download flow through backend signed URLs only.
- Stripe webhook signature enforcement.
- API rate limits for auth, uploads, analysis, exports, admin, and webhook routes.
- Secure guest result link expiry.
- Security response headers.

## Required production environment

```env
DEVBAREUN_ENV=production
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
DEVBAREUN_ADMIN_EMAILS=admin@devbareun.com
DEVBAREUN_ALLOW_ADMIN_EMAIL_FALLBACK=false
DEVBAREUN_ALLOW_DEVBAREUN_DOMAIN_ADMINS=false
DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false
STRIPE_SECRET_KEY=sk_live_or_test_key
STRIPE_WEBHOOK_SECRET=whsec_...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=devbareun-project-files
```

## Supabase steps

1. Run schema and migrations through `database/2026_05_27_v139_production_security.sql`.
2. Keep `devbareun-project-files` private.
3. Add `is_admin=true` to the admin user's metadata or public `users` row.
4. Confirm anonymous users cannot select from `projects`, `uploaded_files`, `reports`, or `guest_orders`.

## Stripe steps

1. Create a Stripe webhook endpoint pointing to `/api/payments/webhook`.
2. Copy the webhook signing secret into `STRIPE_WEBHOOK_SECRET`.
3. Keep `DEVBAREUN_ALLOW_UNSIGNED_STRIPE_WEBHOOK=false` for production.

## Protected file access rule

Frontend must not open Supabase storage paths directly. It should ask backend:

`POST /api/storage/create-download-url`

The backend checks ownership, file status, and storage path before creating a short-lived signed URL.

## Rate limit defaults

| Bucket | Default limit / minute |
|---|---:|
| Auth | 20 |
| Upload | 30 |
| Analysis | 20 |
| Export | 60 |
| Admin | 120 |
| Webhook | 100 |
| Default API | 180 |

For multi-instance production, replace in-memory rate limiting with Redis or a platform edge limiter.
