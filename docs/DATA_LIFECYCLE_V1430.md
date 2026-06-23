# v1.4.30 — Data Lifecycle, Retention and Privacy Requests

## Scope

This release introduces an auditable **request and review workflow** for privacy
exports and erasure requests, plus retention metadata for soft-deleted project
resources. It deliberately does **not** make a browser click destroy storage,
Supabase Auth identities, payment records, immutable audit events or backups.

## Customer API

Authenticated customers can read their policy and create only their own
requests:

```text
GET  /api/privacy/policy
GET  /api/privacy/requests
POST /api/privacy/export-requests
POST /api/privacy/erasure-requests
POST /api/privacy/requests/{request_id}/cancel
```

`scope` is either `account` or `project`. A project-scoped request requires a
project the requester owns. An erasure request requires this exact confirmation:

```text
ERASE MY DATA
```

A second active request of the same type/scope/project returns the existing
request instead of creating duplicates.

## Owner review

Only the canonical `owner` role has the `privacy` capability. The internal
review queue is available through:

```text
GET   /api/admin/data-lifecycle/requests
PATCH /api/admin/data-lifecycle/requests/{request_id}
GET   /api/super-admin/data-lifecycle/requests
PATCH /api/super-admin/data-lifecycle/requests/{request_id}
```

Valid review states are `in_review`, `approved` and `rejected`. An approved
erasure request gets a `scheduled_purge_at` equal to the configured grace
deadline. A cancelled, rejected or completed request is terminal; a new request
must be created instead of reopening it.

## Retention policy

Configure the same values on Railway web, analysis worker and audit archive
worker services:

```env
DEVBAREUN_SOFT_DELETE_RETENTION_DAYS=30
DEVBAREUN_ERASURE_GRACE_DAYS=14
DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS=7
DEVBAREUN_AUTO_PURGE_ENABLED=false
```

Bounds:

| Setting | Allowed range | Default |
|---|---:|---:|
| `DEVBAREUN_SOFT_DELETE_RETENTION_DAYS` | 7–365 days | 30 |
| `DEVBAREUN_ERASURE_GRACE_DAYS` | 1–90 days | 14 |
| `DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS` | 1–30 days | 7 |

`DEVBAREUN_AUTO_PURGE_ENABLED` is an explicit policy visibility flag only in
v1.4.30. There is no automatic destructive purge worker in this release.

When a project or uploaded file is soft-deleted, the API records:

```text
deleted_at
purge_after_at
retention_status=soft_deleted
```

The future physical purge process must be implemented as a separately reviewed
operator workflow. It must honour legal/accounting obligations, report snapshot
integrity, backup retention and the append-only audit chain.

## Data boundaries

The customer API never returns:

```text
requester_user_id
review_note
reviewed_by
storage paths
signed URLs
export payloads
raw file content
provider secrets
```

The owner queue omits raw export payloads and storage paths. Every request,
cancellation and owner review writes a privacy-safe audit event.

## Deployment

1. Apply `database/2026_06_21_v1430_data_lifecycle_requests.sql` after v1.4.25.
2. Set the four policy variables identically on Railway web/analysis/archive services.
3. Run `python tools/check_data_lifecycle.py --root .`.
4. Verify customer request creation with a pilot account and owner review with an
   owner account before enabling any future physical purge automation.
