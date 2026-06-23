# Audit Integrity v1.4.24

## Purpose

v1.4.24 upgrades new internal audit events from ordinary rows to an **append-only, tamper-evident** chain. It is designed for review of privileged Super Admin actions such as staff changes, customer suspension, credit adjustments and analysis recovery.

This is not external non-repudiation. A database superuser with direct production access could still alter both data and chain values. The control is intended to make accidental or unauthorized application/database mutations visible and to prevent ordinary update/delete operations against audit records.

## What is stored

Every new v1 audit event stores:

- actor email, canonical role and, where available, actor user identifier;
- action, entity type and entity identifier;
- bounded/redacted metadata plus `metadata_sha256`;
- request ID, API origin and a bounded request context;
- `previous_event_hash` and `event_hash`;
- integrity version, event category and severity.

The backend does **not** record bearer tokens, cookies, passwords, API keys, service-role secrets or raw request bodies. Metadata keys matching secret-like names are redacted before persistence.

## Database behavior

Apply `database/2026_06_20_v1424_audit_integrity.sql` after v1.4.23.

The migration adds two RPCs:

```text
append_audit_event
  Creates a v1 audit event under a transaction-scoped advisory lock.

audit_integrity_status
  Recomputes the bounded v1 chain for the owner-only internal panel.
```

A database trigger rejects direct `UPDATE` and `DELETE` operations on `public.audit_logs`. New production events are written through `append_audit_event`; older audit rows remain readable as legacy `integrity_version=0` records.

## Request correlation

The backend assigns `X-Request-ID` to every API response. A caller can provide an ID only when it matches the allowed bounded syntax; otherwise the backend generates a UUID. The ID is stored in the event chain and is useful for matching a user-visible request with Railway/API logs.

## Owner review

Only the canonical `owner` role has the `audit` permission. The Super Admin UI exposes:

```text
GET /api/super-admin/audit-integrity
GET /api/super-admin/audit-logs
```

The integrity response intentionally hides IP address and user-agent values from normal table rows. It reports whether the checked chain is valid, the number of events checked, the requested bound and the first broken audit ID when verification fails.

## Operational guidance

- Treat a `verified=false` result as a production incident until investigated.
- Preserve the failing `X-Request-ID`, audit ID and Railway log window.
- Do not attempt to repair audit rows through direct SQL. Export the evidence first, then use a controlled migration/recovery procedure.
- The verification RPC is bounded to 10,000 records. Use a dedicated offline/controlled audit export for very large histories.
