# DevBareun v1.4.16 Analysis Worker Operations

## Purpose

This release makes worker liveness and long-running job execution observable without exposing customer data, uploaded-file paths, payment details, or service-role secrets.

## Migration

Apply `database/2026_06_19_v1416_analysis_worker_observability.sql` after the prior production migrations. It adds `analysis_worker_heartbeats` with RLS enabled and no direct browser read policy.

## Heartbeats

A claimed job updates `analysis_jobs.last_heartbeat_at` at every progress checkpoint and during long parser/analytics execution. Defaults:

| Setting | Default | Safe range |
|---|---:|---:|
| `DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS` | 60 seconds | 10–600 seconds |
| `DEVBAREUN_ANALYSIS_WORKER_STATUS_STALE_SECONDS` | 90 seconds | 30–3600 seconds |
| `DEVBAREUN_ANALYSIS_WORKER_STALE_AFTER_MINUTES` | 45 minutes | Set by CLI |

Keep the heartbeat interval comfortably below the stale timeout.

## Staff operations endpoint

`GET /api/analysis/operations` requires an owner/staff role. It returns only aggregate queue counts and safe worker liveness fields. A healthy production state has:

- `execution_mode` = `worker`;
- `healthy_worker_count` >= 1;
- recent `last_seen_at`;
- no sustained queue growth;
- no repeated stale requeues or failed jobs.

## Failure response

The worker records `degraded` when a polling pass fails and `stopped` when the process exits normally. Use Railway logs to determine root cause; do not copy production exception text into customer-facing job errors. The job service keeps sanitized error behavior in production.

## Manual checks

```bash
python -m app.analysis_worker --once
python -m app.analysis_worker --loop --interval 10 --batch-size 1
python tools/check_database_contract.py --root .
```

After a real analysis request, inspect the protected operations endpoint and verify that the job reaches `completed` before credits are consumed.


## v1.4.17 recovery policy

Apply `database/2026_06_19_v1417_analysis_job_recovery.sql` after v1.4.16. Stale jobs with attempts remaining are requeued; exhausted jobs become `dead_lettered`. Staff review metadata with `GET /api/analysis/operations/recovery-jobs` and explicitly requeue one job with `POST /api/analysis/operations/jobs/{job_id}/retry`. Details: `docs/ANALYSIS_JOB_RECOVERY_V1417.md`.
