-- DevBareun v1.4.5 durable analysis worker bridge
-- Run after 2026_06_18_v142_canonical_api_bridge.sql.

alter table public.analysis_jobs add column if not exists worker_id text;
alter table public.analysis_jobs add column if not exists locked_at timestamptz;
alter table public.analysis_jobs add column if not exists last_heartbeat_at timestamptz;
alter table public.analysis_jobs add column if not exists attempts integer not null default 0;
alter table public.analysis_jobs add column if not exists max_attempts integer not null default 3;
alter table public.analysis_jobs add column if not exists user_payload jsonb not null default '{}'::jsonb;

create index if not exists idx_analysis_jobs_queue_v145
  on public.analysis_jobs(status, created_at)
  where status in ('queued', 'running');

create index if not exists idx_analysis_jobs_worker_lock_v145
  on public.analysis_jobs(worker_id, locked_at)
  where worker_id is not null;

create index if not exists idx_analysis_jobs_stale_v145
  on public.analysis_jobs(status, last_heartbeat_at, locked_at, started_at)
  where status = 'running';
