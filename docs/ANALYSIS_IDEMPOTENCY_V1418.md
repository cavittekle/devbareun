# DevBareun v1.4.18 Analysis Idempotency and Billing Integrity

## Purpose

A duplicate click, browser retry, timeout, or worker crash must not create parallel analysis jobs or consume a subscription/credit twice. This release introduces two complementary controls:

1. `Idempotency-Key` replay handling for `POST /api/analysis/start/{project_id}`.
2. A database-side usage ledger and RPC that atomically records one completed-job entitlement consumption.

## Migration

Run after v1.4.17:

```text
database/2026_06_19_v1418_analysis_idempotency.sql
```

The migration adds request/billing state columns to `analysis_jobs`, a unique replay index and an active-job database guard, `analysis_usage_ledger`, and `consume_analysis_usage_once`.

## API behavior

Clients should send a printable ASCII `Idempotency-Key` no longer than 128 characters. The React and static clients generate one automatically for every analysis-start request.

- Same key + same request: returns the existing job with `idempotent_replay: true`.
- Same key + different project/analysis type: returns HTTP `409 idempotency_key_reused`.
- No key but an active queued/running job already exists for the project: returns that job with `active_job_reused: true`.

## Atomic usage ledger

`consume_analysis_usage_once` locks the job row, checks the unique `analysis_usage_ledger.job_id`, then updates either the active subscription counter or one available credit in the same transaction. Repeated calls return the prior ledger state rather than decrementing again.

The worker reconciles a saved result with pending billing before marking it complete after a crash. This avoids both duplicate charges and silently free completed analyses.

## Operator notes

- Apply the v1.4.18 migration before deploying backend code in production.
- A job with `billing_status=pending` and a saved result should be allowed to reconcile through the worker; do not manually rerun parser work.
- If the atomic RPC is unavailable in production, the job remains failed for review rather than falling back to non-atomic billing.
