-- DevBareun v1.4.17 analysis job recovery and dead-letter bridge
-- Run after 2026_06_19_v1416_analysis_worker_observability.sql.
-- Additive/idempotent: preserves existing analysis job rows.

alter table public.analysis_jobs add column if not exists requeue_count integer not null default 0;
alter table public.analysis_jobs add column if not exists retry_requested_at timestamptz;
alter table public.analysis_jobs add column if not exists retry_requested_by text;
alter table public.analysis_jobs add column if not exists terminal_reason text;

-- Failed/dead-letter jobs are reviewed through protected FastAPI staff endpoints;
-- this index keeps operations/recovery queries bounded as the queue grows.
create index if not exists idx_analysis_jobs_recovery_v1417
  on public.analysis_jobs(status, updated_at desc)
  where status in ('failed', 'dead_lettered');

create index if not exists idx_analysis_jobs_retry_requested_v1417
  on public.analysis_jobs(retry_requested_at desc)
  where retry_requested_at is not null;
