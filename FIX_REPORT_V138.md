# DevBareun v1.3.8 — Admin Panel

## Reason for correction

The official roadmap for the next releases is:

- v1.3.8 — Admin Panel
- v1.3.9 — Production Security
- v1.4.0 — Real SaaS Launch Package
- v1.4.1 — Analytics Polish
- v1.4.2 — PMO / Portfolio Dashboard

The earlier billing/usage work is preserved as foundation logic, but the official v1.3.8 release is now the Admin Panel package.

## Added

- Protected `admin.html` operational console.
- Admin KPI cards for users, companies, projects, payments, reports, failed uploads, credit usage and activity logs.
- Admin module tabs with searchable tables.
- Pilot admin session helper for staging.
- Backend admin endpoints protected by bearer token and admin role checks.
- Admin allowlist support through `DEVBAREUN_ADMIN_EMAILS`.
- Supabase migration for admin support fields and indexes.

## Backend endpoints

- `GET /api/admin/me`
- `GET /api/admin/overview`
- `GET /api/admin/users`
- `GET /api/admin/companies`
- `GET /api/admin/projects`
- `GET /api/admin/payments`
- `GET /api/admin/reports`
- `GET /api/admin/failed-uploads`
- `GET /api/admin/credit-usage`
- `GET /api/admin/activity-logs`

## QA

- Python compile passed for changed backend modules.
- FastAPI route smoke test passed.
- Admin role protection test passed: no token = 401, non-admin token = 403, admin token = 200.
- Frontend admin JS syntax check passed.
