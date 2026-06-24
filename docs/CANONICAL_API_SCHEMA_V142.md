# DevBareun v1.4.2 Canonical API and Schema Cleanup

This refactor finishes the second cleanup pass after the backend route split.

## Canonical customer API

The workspace should use these route families only:

| Area | Canonical route |
| --- | --- |
| Auth | `/api/auth/supabase/login`, `/api/auth/supabase/register`, `/api/auth/me`, `/api/auth/logout` |
| Projects | `/api/projects/create`, `/api/projects/list`, `/api/projects/{project_id}` |
| Uploads | `/api/uploads/create-url`, `/api/uploads/mark-uploaded`, `/api/uploads/project/{project_id}`, `DELETE /api/uploads/{file_id}` |
| Analysis | `POST /api/analysis/start/{project_id}`, `GET /api/analysis/jobs/{job_id}`, `GET /api/analysis/results/{project_id}` |
| Dashboard | `/api/dashboard/portfolio`, `/api/dashboard/executive/{project_id}` |
| Reports | `/api/reports/project/{project_id}`, `/api/reports/generate/{project_id}`, `/api/reports/{report_id}/download` |
| Billing | `/api/billing/create-one-time-checkout`, `/api/billing/create-subscription-checkout`, `/api/billing/status`, `/api/billing/usage`, `/api/billing/webhook` |

Legacy project endpoints remain isolated in `backend/app/legacy_routes.py` and stay disabled unless explicitly enabled with `DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=true`.

## Backend changes

- `/api/projects/list` now reads production Supabase `projects` rows when `SUPABASE_SERVICE_ROLE_KEY` is configured. The previous version listed only the local development store while `projects/create` wrote to production.
- `/api/projects/{project_id}` now reads project detail, uploaded files and analysis results from production Supabase when configured.
- Production project rows are normalized to include compatibility fields such as `project_id`, `project_status`, `client`, `contractor`, and `end_date`.
- Billing credit consumption now updates both canonical and legacy credit counters:
  - `amount` / `remaining`
  - `total_credits` / `used_credits` / `remaining_credits`
- Admin credit totals now read both counter families.

## Frontend changes

- React workspace analysis starts through `POST /api/analysis/start/{project_id}` instead of the older `/api/analysis/create` queue stub.
- Guest result loading uses `/api/guest-result/{token}`.
- Billing checkout reads both `checkout_url` and `url` to support the backend billing service response.
- Static `frontend/js/devbareun-api.js` now routes project creation, upload, preflight and analysis helpers to canonical endpoints instead of disabled legacy project endpoints.

## Database migration

Run the new bridge migration after v1.4.1:

```text
2026_06_18_v142_canonical_api_bridge.sql
```

The migration is additive and idempotent. It adds compatibility columns needed by both the old v1.3 public-id model and the new v1.4 UUID/service-role backend model. It does not remove old columns.

## Deployment order

See `database/SUPABASE_DEPLOY_ORDER.md`. The current production order is:

1. `2026_05_29_v140_production_saas_core.sql`
2. `2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `2026_06_08_v141_super_admin_workspace.sql`
4. `2026_06_18_v142_canonical_api_bridge.sql`
5. `seed_plans.sql`
6. `promote_owner_info_devbareun.sql`
7. `production_rls_audit.sql`
