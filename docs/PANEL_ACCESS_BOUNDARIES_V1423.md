# Panel Access Boundaries v1.4.23

DevBareun has two protected product areas:

- **Customer Workspace**: customer-owned projects, uploads, analyses, reports, billing and settings.
- **Super Admin**: internal operational modules available only to active staff profiles.

This release makes the backend policy canonical and capability-based. A generic “staff” bypass is no longer permitted for customer project data.

## Canonical roles

| Role | Purpose |
| --- | --- |
| `customer` | Own workspace data only. |
| `owner` | Full internal panel and workforce operations. |
| `support` | Customer support, customer status, tickets, notes and activity only. |
| `analyst` | Projects, uploads, reports and activity. |
| `finance` | Payments, credits and activity. |
| `operator` | Projects, reports, activity and analysis-worker operations. |

Legacy `admin` is normalized to `owner`; legacy `user` is normalized to `customer` by the v1.4.23 migration.

## Least-privilege boundaries

- Support and finance roles cannot access another customer’s project, upload object, analysis result or report download.
- Analyst can access project files and reports, but cannot access payments, credits, staff records or worker recovery controls.
- Operator can access projects/reports and worker queue/recovery operations, but cannot access uploads, payments, credits or staff records.
- Manual analysis retry, worker health and dead-letter inspection require the explicit `operations` capability (`owner` or `operator`).
- The customer-status endpoint refuses to mutate any staff account. Staff roles/statuses must be changed only through owner-only staff management.
- A staff account must still be `active` and have a valid authenticated session. UI tab hiding is not authorization; backend routes enforce the same policy.

## Database migration

Apply this after `2026_06_19_v1422_analysis_input_provenance.sql`:

```text
2026_06_20_v1423_panel_access_boundaries.sql
```

The migration normalizes legacy labels, sets the default role to `customer`, adds a canonical role check constraint and creates a small active-role index. It does not grant any new access.

## Operational verification

1. Log in with a `support` account: `/api/super-admin/payments` and `/api/analysis/operations` must return `403`.
2. Log in with a `finance` account: a customer project route and report download for another owner must return `403`.
3. Log in with an `analyst` account: project/upload/report routes may be accessible; payments, credits and operations must return `403`.
4. Log in with an `operator` account: `/api/analysis/operations` may be accessible; upload routes must return `403`.
5. Attempt to suspend an owner/staff user through `PATCH /api/admin/customers/{email}/status`: it must return `403`.

Run the static release contract:

```bash
python tools/check_panel_access_boundaries.py --root .
```
