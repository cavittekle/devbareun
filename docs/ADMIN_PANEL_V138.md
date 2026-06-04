# DevBareun v1.3.8 — Admin Panel

This release converts the placeholder `admin.html` page into a protected SaaS operations console.

## Admin modules

- Users
- Companies
- Projects
- Payments and checkout sessions
- Reports
- Failed uploads
- Credit usage
- Activity logs

## Backend endpoints

All admin endpoints require `Authorization: Bearer <token>` and an admin user.

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

## Admin access rules

A user is treated as admin when one of these is true:

1. Supabase user metadata includes `is_admin: true`.
2. Email is included in the `DEVBAREUN_ADMIN_EMAILS` environment variable.
3. Pilot/dev email ends with `@devbareun.com`.

## Frontend files

- `frontend/admin.html`
- `frontend/js/admin-panel.js`
- `frontend/css/admin-panel.css`

## Supabase migration

Apply:

```sql
\i database/2026_05_27_v138_admin_panel.sql
```

For a fresh deployment, apply the schema and migrations in this order:

1. `database/supabase_schema.sql`
2. `database/seed_plans.sql`
3. `database/2026_05_27_v136_persistent_analysis.sql`
4. `database/2026_05_27_v137_report_archive_print.sql`
5. `database/2026_05_27_v138_billing_gate_usage.sql`
6. `database/2026_05_27_v138_admin_panel.sql`
