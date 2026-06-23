# DevBareun v1.4.5 Analysis Worker

This release keeps the current FastAPI `BackgroundTasks` path available, but adds a durable table-backed worker mode for production.

## Why

Long parsing and analytics jobs should not depend on the lifecycle of the HTTP request process. In v1.4.5, `/api/analysis/start/{project_id}` can enqueue a row in `analysis_jobs`, and a separate worker process can claim and execute queued jobs.

## Execution modes

Configure the backend with:

```text
DEVBAREUN_ANALYSIS_JOB_MODE=background
```

Supported values:

| Mode | Behavior | Intended use |
|---|---|---|
| `background` | API creates the job and schedules FastAPI `BackgroundTasks`. | Existing/default behavior, local/staging. |
| `worker` | API creates the job only. A separate worker process executes queued jobs. | Production durable mode. |
| `inline` | API creates and executes the job synchronously before responding. | Local debugging only. |

## Required migration

Run this after the v1.4.2 bridge migration:

```text
database/2026_06_18_v145_analysis_worker.sql
```

It adds:

```text
analysis_jobs.worker_id
analysis_jobs.locked_at
analysis_jobs.last_heartbeat_at
analysis_jobs.attempts
analysis_jobs.max_attempts
analysis_jobs.user_payload
```

## Railway setup

Use two Railway services from the same `backend` root.

### Web service

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Production env:

```text
DEVBAREUN_ANALYSIS_JOB_MODE=worker
```

### Worker service

```text
python -m app.analysis_worker --loop --interval 10 --batch-size 1
```

Optional env/config:

```text
DEVBAREUN_ANALYSIS_WORKER_INTERVAL=10
DEVBAREUN_ANALYSIS_WORKER_BATCH_SIZE=1
```

## Worker behavior

The worker:

1. requeues stale `running` jobs if their heartbeat/lock is older than the stale threshold;
2. claims queued jobs by updating `status='queued'` to `status='running'`;
3. runs the same parser/analytics/risk/save/credit-consumption pipeline as the existing API background task;
4. marks the job `completed` or `failed`;
5. stores sanitized errors in production security mode.

Default stale timeout:

```text
45 minutes
```

CLI override:

```text
python -m app.analysis_worker --loop --stale-after-minutes 60
```

## Operational notes

- Do not run `DEVBAREUN_ANALYSIS_JOB_MODE=background` and the worker service against the same production database unless duplicate execution has been explicitly tested.
- The recommended production mode is queue-only web service plus one worker service.
- Start with `--batch-size 1`; increase only after real parser runtime and memory usage are measured.
- Worker mode still uses the same `analysis_jobs`, `analysis_results`, `risks`, `uploaded_files`, `analysis_credits`, and `subscriptions` tables.


## v1.4.16 observability and long-running heartbeat

Run the additive migration after v1.4.13:

```text
database/2026_06_19_v1416_analysis_worker_observability.sql
```

It creates `analysis_worker_heartbeats`, a service-role operational table that records worker liveness without exposing it directly to browser users. The protected staff endpoint is:

```text
GET /api/analysis/operations
```

Long-running parser execution now refreshes `analysis_jobs.last_heartbeat_at` at a bounded interval. Configure only when needed:

```text
DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS=60
DEVBAREUN_ANALYSIS_WORKER_STATUS_STALE_SECONDS=90
```

Use values below the job stale timeout. A worker shown as `degraded` or `stopped` should be inspected in Railway logs before retrying customer jobs.
