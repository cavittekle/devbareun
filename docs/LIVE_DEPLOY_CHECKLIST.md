# Live Deploy Checklist

Use this as the final pre-launch runbook.

Provider-specific live values are listed in `docs/LIVE_PROVIDER_SETUP_LIST.md`.

## 1. Deploy Roots

- [ ] Repository root is not deployed.
- [ ] Root `index.html` does not exist.
- [ ] Vercel Root Directory is `frontend`.
- [ ] Railway Root Directory is `backend`.
- [ ] `frontend/vercel.json` is detected by Vercel.
- [ ] Vercel build command runs `npm run build` from `frontend`.
- [ ] `/workspace/` serves the generated React customer workspace.
- [ ] `backend/railway.json` is detected by Railway.

## 2. Domains

- [ ] Frontend domain points to Vercel: `devbareun.com`.
- [ ] `www.devbareun.com` redirects to `devbareun.com`.
- [ ] Backend domain points to Railway.
- [ ] Backend URL is `https://devbareun-production.up.railway.app`.
- [ ] Frontend domains are included in `DEVBAREUN_ALLOWED_ORIGINS`.
- [ ] Frontend domains are included in `DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS`.

## 3. Railway Backend

- [ ] Root Directory is `backend`.
- [ ] `/api/health` returns success.
- [ ] `/api/saas/health` returns success.
- [ ] Health does not show `database: not_configured`.
- [ ] Health does not show `storage: not_configured`.
- [ ] Logs show no missing production secrets.
- [ ] `DEVBAREUN_PRODUCTION_SECURITY=true`.
- [ ] `DEVBAREUN_ENABLE_DEV_AUTH=false`.
- [ ] `DEVBAREUN_ENABLE_LOCAL_STORE=false`.
- [ ] `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`.
- [ ] `DEVBAREUN_ENABLE_PILOT_LOGIN=false`.
- [ ] `DEVBAREUN_ENABLE_PILOT_CHECKOUT=false`.
- [ ] `DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=false`.
- [ ] `DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD=false`.
- [ ] `DEVBAREUN_DISABLE_DOCS=true`.

## 4. Vercel Frontend

- [ ] Root Directory is `frontend`.
- [ ] `index.html` loads.
- [ ] `/workspace/?view=login` loads the React login screen.
- [ ] `/workspace/?view=register` loads the React account screen.
- [ ] Legacy auth URLs redirect to the React workspace auth screens.
- [ ] Pricing buttons route to the correct checkout or account flow.
- [ ] Loader does not get stuck on landing or auth pages.
- [ ] No backend-only secret exists in Vercel environment variables.
- [ ] No service role key exists in frontend source.

## 5. Supabase

- [ ] SQL files are applied using `database/SUPABASE_DEPLOY_ORDER.md`.
- [ ] `database/production_rls_audit.sql` has been run and reviewed.
- [ ] RLS policies are reviewed.
- [ ] Private bucket `project-files` exists.
- [ ] Private bucket `reports` exists if report archive storage is used.
- [ ] `SUPABASE_URL` is set in Railway.
- [ ] `SUPABASE_ANON_KEY` is set in Railway.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is set only in Railway.
- [ ] `SUPABASE_STORAGE_BUCKET=project-files`.
- [ ] Upload test reaches Supabase Storage.
- [ ] No service role key exists in frontend files, Vercel vars, browser code, or screenshots.

## 6. Lemon Squeezy

- [ ] Store is active for live payments.
- [ ] `DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy`.
- [ ] `LEMON_SQUEEZY_STORE_ID=396148`.
- [ ] `LEMON_SQUEEZY_SINGLE_VARIANT_ID=1741208`.
- [ ] `LEMON_SQUEEZY_PLUS_VARIANT_ID=1741246`.
- [ ] `LEMON_SQUEEZY_PRO_VARIANT_ID=1741254`.
- [ ] `LEMON_SQUEEZY_API_KEY` is set only in Railway.
- [ ] `LEMON_SQUEEZY_WEBHOOK_SECRET` is set only in Railway.
- [ ] Webhook endpoint is `/api/billing/webhook`.
- [ ] Test checkout succeeds.
- [ ] Webhook signature verification succeeds.
- [ ] Billing status updates after webhook delivery.

## 7. Final QA

- [ ] `tools/smoke_e2e.ps1` passes against the target frontend/backend URLs.
- [ ] `tools/production_readiness_check.ps1 -FrontendUrl https://devbareun.com -BackendUrl https://devbareun-production.up.railway.app` passes.
- [ ] Single Project upload works without account.
- [ ] Single Project payment unlocks dashboard/report flow.
- [ ] Plus registration creates workspace access.
- [ ] Plus billing redirects correctly.
- [ ] Pro registration creates workspace access.
- [ ] Dashboard, projects, reports, and billing pages are protected.
- [ ] PDF export opens.
- [ ] Excel export opens.
- [ ] Mobile layout remains usable.

## 8. Production Rate Limit

- [ ] `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are configured in Railway.
- [ ] `DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false` in production.
- [ ] A request without Redis in production returns `rate_limiter_not_configured` instead of silently using in-memory limits.
