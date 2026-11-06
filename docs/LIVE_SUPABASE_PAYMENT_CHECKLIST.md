# Supabase + Payment Live Checklist

Use this before switching DevBareun to live traffic.

## Supabase

- [ ] Apply SQL in `database/` using `database/SUPABASE_DEPLOY_ORDER.md`.
- [ ] Create `info@devbareun.com` in Supabase Auth and run `database/promote_owner_info_devbareun.sql`.
- [ ] Run `database/production_rls_audit.sql` and review every `audit_status`.
- [ ] Confirm RLS is enabled on every exposed table.
- [ ] Confirm `anon` and `authenticated` grants match the RLS model.
- [ ] Create private Storage bucket `project-files`.
- [ ] Create private Storage bucket `reports` if report archive storage is used.
- [ ] Set `SUPABASE_URL` in Railway.
- [ ] Set `SUPABASE_ANON_KEY` in Railway.
- [ ] Set `SUPABASE_SERVICE_ROLE_KEY` only in Railway.
- [ ] Set `SUPABASE_STORAGE_BUCKET=project-files`.
- [ ] Verify `GET /api/health` returns `database: connected`.
- [ ] Verify `GET /api/saas/health` does not show `database: not_configured`.
- [ ] Upload a test file and confirm it reaches the private Supabase bucket.
- [ ] Confirm no service role key exists in frontend files, Vercel variables, browser source, screenshots, or docs.

## Payments

- [ ] No online payment provider is connected. Checkout requests return `payments_unavailable`, and plans are activated manually. See `docs/BILLING_LIFECYCLE_V1431.md`.

## Production Flags

- [ ] `DEVBAREUN_PRODUCTION_SECURITY=true`.
- [ ] `DEVBAREUN_ENABLE_DEV_AUTH=false`.
- [ ] `DEVBAREUN_ENABLE_LOCAL_STORE=false`.
- [ ] `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
- [ ] `DEVBAREUN_ENABLE_PILOT_LOGIN=false`.
- [ ] `DEVBAREUN_ENABLE_PILOT_CHECKOUT=false`.
- [ ] `DEVBAREUN_DISABLE_DOCS=true`.

## Final Payment QA

- [ ] Guest Single Project flow reaches checkout without exposing another user's name or email.
- [ ] Checkout success redirects back to DevBareun.
- [ ] Checkout cancel redirects back to DevBareun.
- [ ] Billing status updates after webhook delivery.
- [ ] Duplicate webhook delivery is ignored safely.
- [ ] PDF export works after payment unlock.
- [ ] Excel export works after payment unlock.
