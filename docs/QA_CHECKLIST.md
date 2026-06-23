# QA Checklist

Run this before production deploy.

## Auth And Roles

- Customer login redirects to workspace dashboard.
- Owner login redirects to Super Admin panel.
- Support can see customers, support and activity only.
- Analyst can see projects, uploads, reports and activity only.
- Finance can see payments, credits and activity only.
- Operator can see projects, reports and activity only.
- Customer cannot access `/api/super-admin/...`.
- Unauthorized API calls return 401 or 403.

## Upload And Analysis

- Upload accepts only supported file types.
- Oversized files are rejected.
- File names are sanitized.
- Uploaded file names and progress are visible.
- Analysis starts only when credits/payment allow it.
- Empty dashboard sections are hidden.

## Billing

- Lemon Squeezy checkout opens from backend-generated URL.
- Frontend cannot add credits directly.
- Webhook requires signature verification.
- Credit adjustment writes audit/activity data.

## Production Integrations

- Supabase Auth has a real owner account with `role='owner'` and `status='active'`.
- Supabase Storage bucket exists and upload/download signed URLs work.
- Supabase RLS policies are applied and customer rows are isolated.
- Upstash Redis variables are set before `DEVBAREUN_PRODUCTION_SECURITY=true` launch.
- Lemon Squeezy live checkout and webhook are tested with a real dashboard unlock.

## Reports

- Customer sees only their own reports.
- Staff sees report modules according to role.
- PDF and Excel exports return user-safe errors if storage is missing.

## Frontend Smoke

- `index.html` loads without console errors.
- `/workspace/?view=login` and `/workspace/?view=register` load the React auth screens.
- Header and footer are consistent across public pages.
- Mobile menu works at 360px, 390px and 430px widths.
- EN/AZ language switch remains readable.

## Commands

```powershell
node --check frontend/js/modern-landing.js
node --check frontend/js/admin-panel.js
npm run build --prefix frontend
python -m compileall backend/app
python -m pytest backend/tests
.\tools\smoke_e2e.ps1 -FrontendBase https://devbareun.com -BackendBase https://devbareun-production.up.railway.app
git diff --check
```
