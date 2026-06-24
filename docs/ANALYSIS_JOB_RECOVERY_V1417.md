# DevBareun v1.4.17 Analysis Job Recovery

## Purpose

This release prevents a stale worker from returning the same analysis job to the queue forever. It makes terminal job recovery explicit, reviewable, and safe against duplicated result generation.

## Migration

Run after v1.4.16:

```text
database/2026_06_19_v1417_analysis_job_recovery.sql
```

The migration adds `requeue_count`, `retry_requested_at`, `retry_requested_by`, and `terminal_reason` to `analysis_jobs`, plus recovery indexes. It is additive and idempotent.

## Retry policy

- New jobs use `DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS=3` by default.
- The allowed runtime range is 1–10.
- Every worker claim increments `attempts`.
- A stale running job with remaining attempts returns to `queued` and increments `requeue_count`.
- A stale running job that has exhausted its budget changes to `dead_lettered`.
- A job with an already-persisted result is marked completed instead of being executed again.

## Staff recovery endpoints

```text
GET  /api/analysis/operations
GET  /api/analysis/operations/recovery-jobs?limit=50
POST /api/analysis/operations/jobs/{job_id}/retry
```

All endpoints require an owner/staff role. The recovery list exposes job metadata only: identifiers, status, attempt counters, sanitized error text, timestamps, and whether a completed result exists. It never returns customer payloads, storage paths, or credentials.

### Requeue a normal failed job

```bash
curl -X POST "https://<railway-backend>/api/analysis/operations/jobs/<job-id>/retry" \
  -H "Cookie: devbareun_auth=<staff-session>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Content-Type: application/json" \
  -d '{"reset_attempts": false}'
```

### Requeue a dead-lettered job

Only do this after reviewing Railway logs and confirming the source files are valid:

```bash
curl -X POST "https://<railway-backend>/api/analysis/operations/jobs/<job-id>/retry" \
  -H "Cookie: devbareun_auth=<staff-session>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Content-Type: application/json" \
  -d '{"reset_attempts": true}'
```

The API refuses recovery when a completed result already exists. Resolve the billing/result state manually instead of retrying that job.

## Operator procedure

1. Open `GET /api/analysis/operations` and confirm the worker is healthy.
2. Inspect `GET /api/analysis/operations/recovery-jobs`.
3. Read Railway worker logs for the relevant attempt window.
4. Fix source-file, provider, or configuration issues first.
5. Requeue only the reviewed job. Use `reset_attempts=true` only for `dead_lettered`.
6. Confirm the job reaches `completed` and produces one result.
7. Watch credit usage before marking the support issue resolved.

Do not bulk-retry failed jobs. A failure cluster usually indicates a shared parser, storage, Supabase, or worker configuration issue.
