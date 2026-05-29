-- DevBareun v1.4.0 Production SaaS Core
-- Supabase PostgreSQL foundation for auth profiles, projects, private uploads,
-- analysis jobs/results, reports, billing events and strict owner-based RLS.

create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Core identity and subscription tables
-- ---------------------------------------------------------------------------
create table if not exists public.users_profile (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,
  email text unique not null,
  full_name text,
  role text not null default 'user' check (role in ('user', 'admin')),
  status text not null default 'active' check (status in ('active', 'suspended')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid,
  name text,
  plan text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.companies add column if not exists owner_user_id uuid;
alter table public.companies add column if not exists name text;
alter table public.companies add column if not exists plan text;
alter table public.companies add column if not exists created_at timestamptz default now();
alter table public.companies add column if not exists updated_at timestamptz default now();

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  company_id uuid,
  plan_name text,
  status text,
  monthly_project_limit integer not null default 0,
  used_project_count integer not null default 0,
  current_period_start timestamptz,
  current_period_end timestamptz,
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.subscriptions add column if not exists plan_name text;
alter table public.subscriptions add column if not exists monthly_project_limit integer default 0;
alter table public.subscriptions add column if not exists used_project_count integer default 0;
alter table public.subscriptions add column if not exists current_period_start timestamptz;
alter table public.subscriptions add column if not exists current_period_end timestamptz;
alter table public.subscriptions add column if not exists stripe_customer_id text;
alter table public.subscriptions add column if not exists stripe_subscription_id text;
alter table public.subscriptions add column if not exists owner_email text;
alter table public.subscriptions add column if not exists user_uuid uuid;
alter table public.subscriptions add column if not exists company_uuid uuid;
alter table public.subscriptions add column if not exists created_at timestamptz default now();
alter table public.subscriptions add column if not exists updated_at timestamptz default now();

create table if not exists public.analysis_credits (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  source text,
  credit_type text,
  amount integer not null default 0,
  remaining integer not null default 0,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.analysis_credits add column if not exists source text;
alter table public.analysis_credits add column if not exists credit_type text;
alter table public.analysis_credits add column if not exists amount integer default 0;
alter table public.analysis_credits add column if not exists remaining integer default 0;
alter table public.analysis_credits add column if not exists expires_at timestamptz;
alter table public.analysis_credits add column if not exists owner_email text;
alter table public.analysis_credits add column if not exists user_uuid uuid;

-- ---------------------------------------------------------------------------
-- Project, upload and review tables
-- ---------------------------------------------------------------------------
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  company_id uuid,
  project_name text not null,
  project_code text,
  location text,
  client_name text,
  contractor_name text,
  contract_value numeric,
  currency text not null default 'USD',
  start_date date,
  planned_finish_date date,
  current_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.projects add column if not exists user_id uuid;
alter table public.projects add column if not exists project_code text;
alter table public.projects add column if not exists client_name text;
alter table public.projects add column if not exists contractor_name text;
alter table public.projects add column if not exists planned_finish_date date;
alter table public.projects add column if not exists current_status text;
alter table public.projects add column if not exists owner_email text;
alter table public.projects add column if not exists created_at timestamptz default now();
alter table public.projects add column if not exists updated_at timestamptz default now();

create table if not exists public.uploaded_files (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  bucket text,
  storage_path text not null,
  original_filename text not null,
  file_ext text,
  mime_type text,
  size_bytes bigint,
  upload_status text not null default 'awaiting_upload',
  parser_status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.uploaded_files add column if not exists user_id uuid;
alter table public.uploaded_files add column if not exists bucket text;
alter table public.uploaded_files add column if not exists storage_path text;
alter table public.uploaded_files add column if not exists original_filename text;
alter table public.uploaded_files add column if not exists file_ext text;
alter table public.uploaded_files add column if not exists mime_type text;
alter table public.uploaded_files add column if not exists size_bytes bigint;
alter table public.uploaded_files add column if not exists upload_status text default 'awaiting_upload';
alter table public.uploaded_files add column if not exists parser_status text default 'pending';
alter table public.uploaded_files add column if not exists owner_email text;
alter table public.uploaded_files add column if not exists deleted_at timestamptz;
alter table public.uploaded_files add column if not exists updated_at timestamptz default now();

create table if not exists public.analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  status text not null default 'queued',
  progress integer not null default 0 check (progress >= 0 and progress <= 100),
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

create table if not exists public.analysis_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  job_id uuid,
  normalized_data jsonb not null default '{}'::jsonb,
  dashboard_data jsonb not null default '{}'::jsonb,
  risk_data jsonb not null default '{}'::jsonb,
  confidence_score numeric,
  created_at timestamptz not null default now()
);

alter table public.analysis_results add column if not exists user_id uuid;
alter table public.analysis_results add column if not exists job_id uuid;
alter table public.analysis_results add column if not exists normalized_data jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists dashboard_data jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists risk_data jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists confidence_score numeric;
alter table public.analysis_results add column if not exists owner_email text;

create table if not exists public.risks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  analysis_result_id uuid,
  risk_title text not null,
  category text,
  severity text,
  probability numeric,
  impact text,
  explanation text,
  recommended_action text,
  status text,
  created_at timestamptz not null default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  analysis_result_id uuid,
  report_type text,
  storage_path text,
  status text not null default 'queued',
  created_at timestamptz not null default now()
);

alter table public.reports add column if not exists user_id uuid;
alter table public.reports add column if not exists analysis_result_id uuid;
alter table public.reports add column if not exists storage_path text;
alter table public.reports add column if not exists status text default 'queued';
alter table public.reports add column if not exists owner_email text;

-- ---------------------------------------------------------------------------
-- Billing and audit tables
-- ---------------------------------------------------------------------------
create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  stripe_session_id text,
  stripe_payment_intent_id text,
  stripe_subscription_id text,
  plan_name text,
  amount numeric,
  currency text,
  status text,
  created_at timestamptz not null default now()
);

alter table public.payments add column if not exists stripe_session_id text;
alter table public.payments add column if not exists stripe_payment_intent_id text;
alter table public.payments add column if not exists stripe_subscription_id text;
alter table public.payments add column if not exists plan_name text;
alter table public.payments add column if not exists owner_email text;
alter table public.payments add column if not exists user_uuid uuid;

create table if not exists public.stripe_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text unique not null,
  event_type text,
  processed_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb
);

create table if not exists public.activity_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  project_id uuid,
  action text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.activity_logs add column if not exists user_id uuid;
alter table public.activity_logs add column if not exists project_id uuid;
alter table public.activity_logs add column if not exists action text;
alter table public.activity_logs add column if not exists metadata jsonb default '{}'::jsonb;
alter table public.activity_logs add column if not exists owner_email text;

-- Compatibility defaults for earlier v1.3.x public-id columns that were NOT NULL.
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'projects' and column_name = 'project_id') then
    alter table public.projects alter column project_id set default gen_random_uuid()::text;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'uploaded_files' and column_name = 'file_id') then
    alter table public.uploaded_files alter column file_id set default gen_random_uuid()::text;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'analysis_results' and column_name = 'analysis_id') then
    alter table public.analysis_results alter column analysis_id set default gen_random_uuid()::text;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'reports' and column_name = 'report_id') then
    alter table public.reports alter column report_id set default gen_random_uuid()::text;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'payments' and column_name = 'payment_id') then
    alter table public.payments alter column payment_id set default gen_random_uuid()::text;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'payments' and column_name = 'payment_type') then
    alter table public.payments alter column payment_type set default 'checkout';
    alter table public.payments alter column payment_type drop not null;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
create index if not exists idx_users_profile_auth_user_id on public.users_profile(auth_user_id);
create index if not exists idx_users_profile_email on public.users_profile(lower(email));
create index if not exists idx_users_profile_role on public.users_profile(role);
create index if not exists idx_companies_owner_user_id on public.companies(owner_user_id);
create index if not exists idx_projects_user_id on public.projects(user_id);
create index if not exists idx_projects_owner_email_v140 on public.projects(lower(owner_email));
create index if not exists idx_uploads_user_id on public.uploaded_files(user_id);
create index if not exists idx_uploads_project_id_text on public.uploaded_files((project_id::text));
create index if not exists idx_uploads_storage_path_v140 on public.uploaded_files(storage_path);
create index if not exists idx_jobs_user_project on public.analysis_jobs(user_id, project_id);
create index if not exists idx_results_user_project on public.analysis_results(user_id, project_id);
create index if not exists idx_risks_user_project on public.risks(user_id, project_id);
create index if not exists idx_reports_user_project on public.reports(user_id, project_id);
create index if not exists idx_stripe_events_event_id on public.stripe_events(stripe_event_id);

-- ---------------------------------------------------------------------------
-- RLS helper functions
-- ---------------------------------------------------------------------------
create or replace function public.current_user_email()
returns text
language sql
stable
as $$
  select lower(coalesce(auth.jwt() ->> 'email', ''));
$$;

create or replace function public.current_profile_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select up.id
  from public.users_profile up
  where up.auth_user_id = auth.uid()
    and up.status = 'active'
  limit 1;
$$;

create or replace function public.user_matches(value text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select
    value is not null
    and lower(value) in (
      lower(coalesce(auth.uid()::text, '')),
      lower(coalesce(public.current_profile_id()::text, '')),
      public.current_user_email()
    );
$$;

create or replace function public.is_admin_user()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.users_profile up
    where up.auth_user_id = auth.uid()
      and up.role = 'admin'
      and up.status = 'active'
  );
$$;

-- ---------------------------------------------------------------------------
-- Enable RLS
-- ---------------------------------------------------------------------------
alter table public.users_profile enable row level security;
alter table public.companies enable row level security;
alter table public.subscriptions enable row level security;
alter table public.analysis_credits enable row level security;
alter table public.projects enable row level security;
alter table public.uploaded_files enable row level security;
alter table public.analysis_jobs enable row level security;
alter table public.analysis_results enable row level security;
alter table public.risks enable row level security;
alter table public.reports enable row level security;
alter table public.payments enable row level security;
alter table public.stripe_events enable row level security;
alter table public.activity_logs enable row level security;

-- ---------------------------------------------------------------------------
-- RLS policies, strict owner/admin access
-- ---------------------------------------------------------------------------
drop policy if exists users_profile_owner_or_admin on public.users_profile;
create policy users_profile_owner_or_admin on public.users_profile
for all using (auth.uid() = auth_user_id or public.is_admin_user())
with check (auth.uid() = auth_user_id or public.is_admin_user());

drop policy if exists companies_owner_or_admin_v140 on public.companies;
create policy companies_owner_or_admin_v140 on public.companies
for all using (public.is_admin_user() or public.user_matches(owner_user_id::text))
with check (public.is_admin_user() or public.user_matches(owner_user_id::text));

drop policy if exists subscriptions_owner_or_admin_v140 on public.subscriptions;
create policy subscriptions_owner_or_admin_v140 on public.subscriptions
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
);

drop policy if exists credits_owner_or_admin_v140 on public.analysis_credits;
create policy credits_owner_or_admin_v140 on public.analysis_credits
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
);

drop policy if exists projects_owner_or_admin_v140 on public.projects;
create policy projects_owner_or_admin_v140 on public.projects
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
);

drop policy if exists uploaded_files_owner_or_admin_v140 on public.uploaded_files;
create policy uploaded_files_owner_or_admin_v140 on public.uploaded_files
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
);

drop policy if exists analysis_jobs_owner_or_admin_v140 on public.analysis_jobs;
create policy analysis_jobs_owner_or_admin_v140 on public.analysis_jobs
for all using (public.is_admin_user() or public.user_matches(user_id::text))
with check (public.is_admin_user() or public.user_matches(user_id::text));

drop policy if exists analysis_results_owner_or_admin_v140 on public.analysis_results;
create policy analysis_results_owner_or_admin_v140 on public.analysis_results
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
);

drop policy if exists risks_owner_or_admin_v140 on public.risks;
create policy risks_owner_or_admin_v140 on public.risks
for all using (public.is_admin_user() or public.user_matches(user_id::text))
with check (public.is_admin_user() or public.user_matches(user_id::text));

drop policy if exists reports_owner_or_admin_v140 on public.reports;
create policy reports_owner_or_admin_v140 on public.reports
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
);

drop policy if exists payments_owner_or_admin_v140 on public.payments;
create policy payments_owner_or_admin_v140 on public.payments
for all using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
)
with check (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, user_uuid::text, owner_email))
);

drop policy if exists stripe_events_admin_only_v140 on public.stripe_events;
create policy stripe_events_admin_only_v140 on public.stripe_events
for all using (public.is_admin_user())
with check (public.is_admin_user());

drop policy if exists activity_logs_owner_or_admin_v140 on public.activity_logs;
create policy activity_logs_owner_or_admin_v140 on public.activity_logs
for select using (
  public.is_admin_user()
  or public.user_matches(coalesce(user_id::text, owner_email))
);

-- ---------------------------------------------------------------------------
-- Private Supabase Storage bucket
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('project-files', 'project-files', false)
on conflict (id) do update set public = false;

drop policy if exists project_files_owner_insert_v140 on storage.objects;
create policy project_files_owner_insert_v140 on storage.objects
for insert with check (
  bucket_id = 'project-files'
  and (
    public.is_admin_user()
    or (storage.foldername(name))[1] = auth.uid()::text
    or (storage.foldername(name))[1] = public.current_profile_id()::text
  )
);

drop policy if exists project_files_owner_read_v140 on storage.objects;
create policy project_files_owner_read_v140 on storage.objects
for select using (
  bucket_id = 'project-files'
  and (
    public.is_admin_user()
    or (storage.foldername(name))[1] = auth.uid()::text
    or (storage.foldername(name))[1] = public.current_profile_id()::text
  )
);

drop policy if exists project_files_owner_delete_v140 on storage.objects;
create policy project_files_owner_delete_v140 on storage.objects
for delete using (
  bucket_id = 'project-files'
  and (
    public.is_admin_user()
    or (storage.foldername(name))[1] = auth.uid()::text
    or (storage.foldername(name))[1] = public.current_profile_id()::text
  )
);
