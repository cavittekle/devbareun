-- DevBareun v1.4.16 analysis worker observability bridge
-- Run after 2026_06_19_v1413_database_contract_bridge.sql.
-- Service-role backend access writes these liveness rows; no browser user policy is granted.

create table if not exists public.analysis_worker_heartbeats (
  worker_id text primary key,
  status text not null default 'online',
  started_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  last_result_at timestamptz,
  processed_jobs integer not null default 0,
  claimed_jobs integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.analysis_worker_heartbeats enable row level security;

-- The application uses the Supabase service role for operations telemetry.
-- Explicitly deny direct authenticated browser reads; staff access is mediated by
-- the protected FastAPI /api/analysis/operations endpoint.
create policy "analysis_worker_heartbeats_no_direct_browser_access"
  on public.analysis_worker_heartbeats
  for select
  to authenticated
  using (false);

create index if not exists idx_analysis_worker_heartbeats_seen_v1416
  on public.analysis_worker_heartbeats(last_seen_at desc);

create index if not exists idx_analysis_worker_heartbeats_status_v1416
  on public.analysis_worker_heartbeats(status, last_seen_at desc);
