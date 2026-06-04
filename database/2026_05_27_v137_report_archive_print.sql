-- DevBareun v1.3.7 Report Archive + A4/A3 Print System

alter table if exists reports
  add column if not exists owner_email text,
  add column if not exists project_name text,
  add column if not exists analysis_type text default 'all',
  add column if not exists print_size text default 'A4',
  add column if not exists print_orientation text default 'portrait',
  add column if not exists title text,
  add column if not exists dashboard jsonb default '{}'::jsonb,
  add column if not exists kpis jsonb default '{}'::jsonb,
  add column if not exists report_payload jsonb default '{}'::jsonb,
  add column if not exists status text default 'archived',
  add column if not exists source text default 'analysis_save',
  add column if not exists created_at_ts bigint;

create index if not exists idx_reports_owner_email on reports(owner_email);
create index if not exists idx_reports_project_id on reports(project_id);
create index if not exists idx_reports_analysis_id on reports(analysis_id);
create index if not exists idx_reports_created_at_ts on reports(created_at_ts desc);

-- Optional RLS read policy for authenticated users once owner_email is filled by backend.
create policy if not exists "reports_read_own_archive" on public.reports
for select using (owner_email = auth.email());
