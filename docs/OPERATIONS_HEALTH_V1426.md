# DevBareun v1.4.26 — Operational Health

## Purpose

This release adds one staff-safe health view for the internal operating model. It joins three existing signals without widening access to tenant or provider data:

- runtime readiness from `runtime_readiness_report()`;
- analysis queue and worker heartbeat status;
- external audit archive queue and archive-worker heartbeat status.

## Endpoints

```text
GET /api/operations/health
GET /api/admin/operations-health
GET /api/super-admin/operations-health
```

All three paths require the canonical `operations` capability. Only `owner` and `operator` receive this capability. The Super Admin alias is used by the Operations health panel tab.

## Status model

| Status | Meaning | Operator response |
|---|---|---|
| `healthy` | No actionable condition | Continue routine monitoring. |
| `degraded` | Worker, retry/dead-letter or readiness warning needs review | Inspect incident code and use the relevant operations/recovery module. |
| `unavailable` | Runtime/store dependency cannot be trusted | Pause privileged recovery actions; inspect Railway/Supabase and incident logs. |
| `disabled` | Optional audit archive is intentionally disabled | Confirm this is a deliberate policy decision. |

## Incident codes

```text
runtime_not_ready
runtime_warning
analysis_store_unavailable
analysis_worker_unavailable
analysis_failed_jobs
analysis_dead_lettered_jobs
audit_archive_store_unavailable
audit_archive_delivery_not_ready
audit_archive_worker_unavailable
audit_archive_dead_lettered
```

The endpoint intentionally returns only status, counts and incident codes. It does not return webhook URLs, HMAC secrets, signed URLs, raw audit payloads, customer records, job payloads or exception text.

## Incident handling

1. Open **Super Admin → Operations health**.
2. Classify the incident by component and code.
3. For analysis failures, use `/api/analysis/operations` and reviewed job retry.
4. For audit archive failures, use **Audit archive**; only an owner can retry a dead-letter event.
5. For `runtime_not_ready` or store unavailability, do not force retries. Correct Railway/Supabase configuration first, then rerun the production smoke test.

This is an aggregation layer only. It does not replace Railway logs, Supabase monitoring or the external audit receiver’s own evidence.
