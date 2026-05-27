
-- DevBareun v1.3.6 Persistent Analysis + Saved Dashboards

alter table if exists projects
  add column if not exists created_at_ts bigint,
  add column if not exists status text default 'active';

alter table if exists analysis_results
  add column if not exists report_payload jsonb,
  add column if not exists dashboard jsonb,
  add column if not exists kpis jsonb,
  add column if not exists created_at_ts bigint,
  add column if not exists status text default 'completed';

alter table if exists guest_orders
  add column if not exists guest_token text unique,
  add column if not exists dashboard jsonb,
  add column if not exists expires_at_ts bigint,
  add column if not exists created_at_ts bigint;

create index if not exists idx_projects_owner_email on projects(owner_email);
create index if not exists idx_analysis_owner_email on analysis_results(owner_email);
create index if not exists idx_analysis_project_id on analysis_results(project_id);
create index if not exists idx_guest_orders_token on guest_orders(guest_token);
