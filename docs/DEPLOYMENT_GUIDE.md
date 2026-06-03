# DevBareun Deployment Guide

## Purpose

This guide explains how to deploy DevBareun safely without exposing secrets.

Recommended deployment direction:

- Frontend: Vercel
- Backend: Railway
- Database/Auth/Storage: Supabase
- Repository: GitHub

## Important Security Rule

Do not commit real secrets to GitHub.

Never commit:

- `.env`
- Supabase service role key
- Supabase JWT secret
- database password
- payment secret key
- webhook secret
- private storage keys
- production credentials

Use `.env.example` only as a variable-name template.

## Environment Files

Local development:

```bash
cp .env.example .env
```

Production:

- Add environment variables directly inside Vercel, Railway, Supabase, or the relevant platform.
- Do not upload `.env` to GitHub.

## Frontend Deployment - Vercel

### Required Values

Frontend-safe values only:

```env
NEXT_PUBLIC_APP_URL=
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

or if using Vite:

```env
VITE_APP_URL=
VITE_API_BASE_URL=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

### Build Settings

Fill based on actual project:

```text
Framework preset:
Root directory:
Build command:
Output directory:
Install command:
```

Common examples:

```text
Build command: npm run build
Output directory: dist
```

or:

```text
Build command: npm run build
Output directory: .next
```

### Frontend Checklist

- [ ] Landing page opens without login.
- [ ] Login/Register buttons work.
- [ ] EN/AZ language switch works.
- [ ] Dark-only public UI is readable.
- [ ] Upload UI is visible.
- [ ] Pricing UI is visible.
- [ ] API base URL points to production backend.
- [ ] No service role key is exposed in frontend.
- [ ] Mobile layout works at 360px, 390px, and 430px.

## Backend Deployment - Railway

### Required Values

Backend-only values:

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
JWT_SECRET=
SESSION_SECRET=
CORS_ALLOWED_ORIGINS=
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_WEBHOOK_SECRET=
```

### Start Settings

Fill based on actual backend:

```text
Root directory:
Install command:
Start command:
Health check path:
```

Possible examples:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

or:

```bash
python -m app.main
```

### Backend Checklist

- [ ] Backend starts successfully.
- [ ] Health check endpoint works.
- [ ] CORS allows production frontend URL.
- [ ] Upload endpoint validates files.
- [ ] Auth-protected endpoints reject unauthenticated users.
- [ ] Admin endpoints reject non-admin users.
- [ ] No secret is logged.
- [ ] Payment webhook signature is verified.
- [ ] Rate limiting is enabled if public APIs exist.

## Supabase Setup

### Required Supabase Items

- Project URL
- Anon key
- Service role key for backend only
- JWT secret for backend only
- PostgreSQL connection string
- Storage bucket for project files
- Storage bucket for reports

### Security Checklist

- [ ] RLS enabled for user-owned tables.
- [ ] Users cannot read other users' projects.
- [ ] Users cannot access other users' uploaded files.
- [ ] Admin policy is explicit.
- [ ] Public buckets contain only public files.
- [ ] Private buckets are protected.
- [ ] Service role key is not used in frontend.

## Database Migration Checklist

Before production:

- [ ] Create migration SQL files.
- [ ] Review table names and relationships.
- [ ] Add indexes for `user_id`, `project_id`, `company_id`, `status`, and `created_at` where useful.
- [ ] Apply migrations on staging first.
- [ ] Test RLS with normal user account.
- [ ] Test admin access separately.
- [ ] Backup production before destructive changes.

## Storage Checklist

Recommended buckets:

```text
project-files
reports
public-assets
```

Access rules:

```text
project-files: private
reports: private
public-assets: public
```

## Payment Deployment

Payment logic must stay backend-side.

Required values:

```env
PAYMENT_PROVIDER=lemon_squeezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_SINGLE_VARIANT_ID=
LEMON_SQUEEZY_PLUS_VARIANT_ID=
LEMON_SQUEEZY_PRO_VARIANT_ID=
LEMON_SQUEEZY_SUCCESS_URL=
LEMON_SQUEEZY_CANCEL_URL=
```

Checklist:

- [ ] Checkout flow works.
- [ ] Success URL works.
- [ ] Cancel URL works.
- [ ] Webhook endpoint works.
- [ ] Webhook signature is verified.
- [ ] Subscription status is saved.
- [ ] Usage limits are updated correctly.
- [ ] Secret key is not exposed in frontend.

## Production Pre-Launch Checklist

- [ ] Frontend build passes.
- [ ] Backend starts without error.
- [ ] CI passes.
- [ ] Health endpoint works.
- [ ] Auth flow tested.
- [ ] Upload flow tested.
- [ ] Parser handles missing fields.
- [ ] Dashboard does not show empty sections.
- [ ] PDF export works.
- [ ] Excel export works.
- [ ] Report archive works.
- [ ] Payment flow works.
- [ ] Admin route is protected.
- [ ] Mobile UI tested.
- [ ] No `.env` committed.
- [ ] No secrets in frontend bundle.
- [ ] Domain and SSL configured.

## Rollback Plan

Last known working commit:

```text

```

Rollback steps:

```text
1. Revert to last known working deployment.
2. Restore database backup if migration caused data issue.
3. Disable payment webhook temporarily if needed.
4. Confirm frontend/backend health checks.
5. Document incident in CHANGELOG.md.
```

## Deployment Notes

Update this section after every successful production deployment.

```text
Date:
Frontend deployment:
Backend deployment:
Database migration:
Known issues:
Rollback commit:
```
