-- DevBareun v1.3.8 — Admin Panel Support
-- Apply after v1.3.8 billing/usage migration if that file has already been applied.

alter table if exists public.users
  add column if not exists last_login_at timestamptz,
  add column if not exists is_admin boolean default false;

alter table if exists public.companies
  add column if not exists status text default 'active',
  add column if not exists owner_email text;

alter table if exists public.projects
  add column if not exists owner_email text,
  add column if not exists status text default 'active',
  add column if not exists payment_status text default 'unpaid',
  add column if not exists access_status text default 'draft';

alter table if exists public.uploaded_files
  add column if not exists owner_email text,
  add column if not exists failure_reason text,
  add column if not exists error_message text,
  add column if not exists upload_progress integer default 0,
  add column if not exists uploaded_at timestamptz;

alter table if exists public.reports
  add column if not exists owner_email text,
  add column if not exists project_name text,
  add column if not exists analysis_type text,
  add column if not exists print_size text default 'A4',
  add column if not exists print_orientation text,
  add column if not exists status text default 'archived',
  add column if not exists title text,
  add column if not exists dashboard jsonb default '{}'::jsonb,
  add column if not exists kpis jsonb default '{}'::jsonb,
  add column if not exists report_payload jsonb default '{}'::jsonb,
  add column if not exists created_at_ts bigint;

alter table if exists public.activity_logs
  add column if not exists actor text,
  add column if not exists owner_email text;

create index if not exists idx_admin_users_email on public.users(email);
create index if not exists idx_admin_users_is_admin on public.users(is_admin);
create index if not exists idx_admin_companies_owner_email on public.companies(owner_email);
create index if not exists idx_admin_projects_owner_email on public.projects(owner_email);
create index if not exists idx_admin_projects_status on public.projects(status);
create index if not exists idx_admin_uploaded_files_status on public.uploaded_files(status);
create index if not exists idx_admin_reports_owner_email on public.reports(owner_email);
create index if not exists idx_admin_reports_project_id on public.reports(project_id);
create index if not exists idx_admin_activity_logs_actor on public.activity_logs(actor);
