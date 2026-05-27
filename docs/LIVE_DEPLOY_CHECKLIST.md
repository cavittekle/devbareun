# Live Deploy Checklist

Use this as the final pre-launch runbook.

## 1. Domains

- [ ] Frontend domain points to Vercel: `devbareun.com`
- [ ] `www.devbareun.com` redirects to `devbareun.com`
- [ ] Backend domain points to Railway
- [ ] Backend URL is included in frontend config and docs
- [ ] Frontend domains are included in `DEVBAREUN_ALLOWED_ORIGINS`
- [ ] Frontend domains are included in `DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS`

## 2. Railway Backend

- [ ] Root Directory is `backend`
- [ ] `backend/railway.json` is detected
- [ ] `/health` returns success
- [ ] `/api/saas/health` returns success
- [ ] Logs show no missing production secrets
- [ ] `DEVBAREUN_PRODUCTION_SECURITY=true`
- [ ] `DEVBAREUN_ENABLE_MOCK_PAYMENT=false`
- [ ] `DEVBAREUN_ENABLE_PILOT_LOGIN=false`
- [ ] `DEVBAREUN_ENABLE_PILOT_CHECKOUT=false`

## 3. Vercel Frontend

- [ ] Root Directory is `frontend`
- [ ] `frontend/vercel.json` is detected
- [ ] `index.html` loads
- [ ] `login.html` loads
- [ ] `register.html` loads
- [ ] Pricing buttons route to the correct checkout or account flow
- [ ] Loader does not get stuck on landing or auth pages

## 4. Supabase

- [ ] SQL files are applied in the documented order
- [ ] RLS policies are reviewed
- [ ] Private bucket `devbareun-project-files` exists
- [ ] `SUPABASE_URL` is set in Railway
- [ ] `SUPABASE_ANON_KEY` is set in Railway
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is set only in Railway
- [ ] No service role key exists in frontend files, Vercel vars or browser code

## 5. Stripe

- [ ] Single Project price exists: `$29`
- [ ] Plus price exists: `$49/month`
- [ ] Pro price exists: `$89/month`
- [ ] Railway has all Stripe price IDs
- [ ] Railway has `STRIPE_WEBHOOK_SECRET`
- [ ] Webhook endpoint is `/api/payments/webhook`
- [ ] Test checkout succeeds
- [ ] Webhook signature verification succeeds
- [ ] Live keys are used only after test mode passes

## 6. Final QA

- [ ] Single Project upload works without account
- [ ] Single Project payment unlocks dashboard/report flow
- [ ] Plus registration creates workspace access
- [ ] Plus billing redirects correctly
- [ ] Pro registration creates workspace access
- [ ] Dashboard, projects, reports and billing pages are protected
- [ ] PDF export opens
- [ ] Excel export opens
- [ ] Light mode remains readable
- [ ] Mobile layout remains usable
