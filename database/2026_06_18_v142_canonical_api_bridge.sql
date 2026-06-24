-- DevBareun v1.4.2 Canonical API Bridge
-- Aligns the Supabase schema with the cleaned backend route families:
--   /api/projects, /api/uploads, /api/analysis, /api/billing, /api/reports
-- This migration is intentionally additive and idempotent. It keeps old v1.3.x
-- public-id columns available while the production API uses UUID primary keys.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Company/profile compatibility columns
-- ---------------------------------------------------------------------------
alter table public.users_profile add column if not exists user_id text default gen_random_uuid()::text;
alter table public.users_profile add column if not exists auth_provider text;
alter table public.users_profile add column if not exists company_id uuid;
alter table public.users_profile add column if not exists plan text default 'free';

alter table public.companies add column if not exists company_id text default gen_random_uuid()::text;
alter table public.companies add column if not exists company_name text;
alter table public.companies add column if not exists contact_person text;
alter table public.companies add column if not exists email text;
alter table public.companies add column if not exists phone text;
alter table public.companies add column if not exists country text;
alter table public.companies add column if not exists subscription_plan text default 'free';
alter table public.companies add column if not exists owner_email text;

update public.companies
set company_name = coalesce(company_name, name),
    subscription_plan = coalesce(subscription_plan, plan, 'free')
where company_name is null or subscription_plan is null;

-- ---------------------------------------------------------------------------
-- Project compatibility columns
-- ---------------------------------------------------------------------------
alter table public.projects add column if not exists project_id text default gen_random_uuid()::text;
alter table public.projects add column if not exists owner_email text;
alter table public.projects add column if not exists owner_user_id text;
alter table public.projects add column if not exists guest_order_id text;
alter table public.projects add column if not exists contractor text;
alter table public.projects add column if not exists client text;
alter table public.projects add column if not exists end_date date;
alter table public.projects add column if not exists duration text;
alter table public.projects add column if not exists project_status text default 'draft';
alter table public.projects add column if not exists analysis_type text default 'all';

update public.projects
set contractor = coalesce(contractor, contractor_name),
    client = coalesce(client, client_name),
    end_date = coalesce(end_date, planned_finish_date),
    project_status = coalesce(project_status, current_status, 'draft')
where contractor is null or client is null or end_date is null or project_status is null;

create unique index if not exists idx_projects_project_id_v142 on public.projects(project_id);
create index if not exists idx_projects_owner_email_v142 on public.projects(lower(owner_email));
create index if not exists idx_projects_status_v142 on public.projects(project_status);

-- ---------------------------------------------------------------------------
-- Upload compatibility columns
-- ---------------------------------------------------------------------------
alter table public.uploaded_files add column if not exists file_id text default gen_random_uuid()::text;
alter table public.uploaded_files add column if not exists storage_bucket text;
alter table public.uploaded_files add column if not exists original_name text;
alter table public.uploaded_files add column if not exists extension text;
alter table public.uploaded_files add column if not exists content_type text;
alter table public.uploaded_files add column if not exists file_size_bytes bigint;
alter table public.uploaded_files add column if not exists checksum text;
alter table public.uploaded_files add column if not exists status text default 'awaiting_upload';
alter table public.uploaded_files add column if not exists owner_email text;
alter table public.uploaded_files add column if not exists uploaded_by_user_id text;
alter table public.uploaded_files add column if not exists deleted_at timestamptz;
alter table public.uploaded_files add column if not exists storage_delete_status text;

update public.uploaded_files
set storage_bucket = coalesce(storage_bucket, bucket),
    original_name = coalesce(original_name, original_filename),
    extension = coalesce(extension, file_ext),
    content_type = coalesce(content_type, mime_type),
    file_size_bytes = coalesce(file_size_bytes, size_bytes),
    status = coalesce(status, upload_status, 'awaiting_upload')
where storage_bucket is null
   or original_name is null
   or extension is null
   or content_type is null
   or file_size_bytes is null
   or status is null;

create unique index if not exists idx_uploaded_files_file_id_v142 on public.uploaded_files(file_id);
create index if not exists idx_uploaded_files_project_id_v142 on public.uploaded_files((project_id::text));
create index if not exists idx_uploaded_files_owner_email_v142 on public.uploaded_files(lower(owner_email));
create index if not exists idx_uploaded_files_status_v142 on public.uploaded_files(status, upload_status, parser_status);

-- ---------------------------------------------------------------------------
-- Analysis jobs/results compatibility columns
-- ---------------------------------------------------------------------------
alter table public.analysis_jobs add column if not exists job_id text default gen_random_uuid()::text;
alter table public.analysis_jobs add column if not exists owner_email text;
alter table public.analysis_jobs add column if not exists analysis_type text default 'all';
alter table public.analysis_jobs add column if not exists updated_at timestamptz default now();
create unique index if not exists idx_analysis_jobs_job_id_v142 on public.analysis_jobs(job_id);
create index if not exists idx_analysis_jobs_owner_email_v142 on public.analysis_jobs(lower(owner_email));
create index if not exists idx_analysis_jobs_project_id_v142 on public.analysis_jobs((project_id::text));

alter table public.analysis_results add column if not exists analysis_id text default gen_random_uuid()::text;
alter table public.analysis_results add column if not exists uploaded_file_ids text[] default '{}';
alter table public.analysis_results add column if not exists result_json jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists dashboard jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists kpis jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists report_payload jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists risk_level text;
alter table public.analysis_results add column if not exists status text default 'completed';
alter table public.analysis_results add column if not exists analysis_type text default 'all';
alter table public.analysis_results add column if not exists owner_email text;
alter table public.analysis_results add column if not exists completed_at timestamptz;

update public.analysis_results
set result_json = case when result_json = '{}'::jsonb then dashboard_data else result_json end,
    dashboard = case when dashboard = '{}'::jsonb then dashboard_data else dashboard end,
    status = coalesce(status, 'completed')
where result_json = '{}'::jsonb or dashboard = '{}'::jsonb or status is null;

create unique index if not exists idx_analysis_results_analysis_id_v142 on public.analysis_results(analysis_id);
create index if not exists idx_analysis_results_owner_email_v142 on public.analysis_results(lower(owner_email));
create index if not exists idx_analysis_results_project_id_v142 on public.analysis_results((project_id::text));

-- ---------------------------------------------------------------------------
-- Reports compatibility columns
-- ---------------------------------------------------------------------------
alter table public.reports add column if not exists report_id text default gen_random_uuid()::text;
alter table public.reports add column if not exists analysis_id text;
alter table public.reports add column if not exists project_name text;
alter table public.reports add column if not exists analysis_type text;
alter table public.reports add column if not exists language text default 'en';
alter table public.reports add column if not exists storage_bucket text;
alter table public.reports add column if not exists report_name text;
alter table public.reports add column if not exists format text default 'PDF';
alter table public.reports add column if not exists media_type text;
alter table public.reports add column if not exists report_payload jsonb default '{}'::jsonb;
alter table public.reports add column if not exists owner_email text;
alter table public.reports add column if not exists download_count integer default 0;
alter table public.reports add column if not exists unlocked_at timestamptz;
create unique index if not exists idx_reports_report_id_v142 on public.reports(report_id);
create index if not exists idx_reports_owner_email_v142 on public.reports(lower(owner_email));
create index if not exists idx_reports_project_id_v142 on public.reports((project_id::text));

-- ---------------------------------------------------------------------------
-- Billing/credit compatibility columns
-- ---------------------------------------------------------------------------
alter table public.subscriptions add column if not exists subscription_id text default gen_random_uuid()::text;
alter table public.subscriptions add column if not exists owner_email text;
alter table public.subscriptions add column if not exists plan_code text;
alter table public.subscriptions add column if not exists monthly_credits integer default 0;
alter table public.subscriptions add column if not exists monthly_project_limit integer default 0;
alter table public.subscriptions add column if not exists used_project_count integer default 0;

update public.subscriptions
set plan_code = coalesce(plan_code, plan_name),
    monthly_credits = coalesce(nullif(monthly_credits, 0), monthly_project_limit, 0)
where plan_code is null or monthly_credits = 0;

create unique index if not exists idx_subscriptions_subscription_id_v142 on public.subscriptions(subscription_id);
create index if not exists idx_subscriptions_owner_email_v142 on public.subscriptions(lower(owner_email));

alter table public.analysis_credits add column if not exists credit_id text default gen_random_uuid()::text;
alter table public.analysis_credits add column if not exists owner_email text;
alter table public.analysis_credits add column if not exists plan_code text;
alter table public.analysis_credits add column if not exists project_id text;
alter table public.analysis_credits add column if not exists total_credits integer default 0;
alter table public.analysis_credits add column if not exists used_credits integer default 0;
alter table public.analysis_credits add column if not exists remaining_credits integer default 0;
alter table public.analysis_credits add column if not exists status text default 'active';
alter table public.analysis_credits add column if not exists period_start timestamptz;
alter table public.analysis_credits add column if not exists period_end timestamptz;

update public.analysis_credits
set total_credits = greatest(coalesce(total_credits, 0), coalesce(amount, 0)),
    remaining_credits = greatest(coalesce(remaining_credits, 0), coalesce(remaining, 0)),
    used_credits = case
      when coalesce(used_credits, 0) > 0 then used_credits
      else greatest(0, greatest(coalesce(total_credits, 0), coalesce(amount, 0)) - greatest(coalesce(remaining_credits, 0), coalesce(remaining, 0)))
    end,
    status = coalesce(status, 'active')
where coalesce(total_credits, 0) = 0
   or coalesce(remaining_credits, 0) = 0
   or status is null;

create unique index if not exists idx_analysis_credits_credit_id_v142 on public.analysis_credits(credit_id);
create index if not exists idx_analysis_credits_owner_email_v142 on public.analysis_credits(lower(owner_email));
create index if not exists idx_analysis_credits_status_v142 on public.analysis_credits(status);

alter table public.payments add column if not exists payment_id text default gen_random_uuid()::text;
alter table public.payments add column if not exists owner_email text;
alter table public.payments add column if not exists checkout_id text;
alter table public.payments add column if not exists plan_code text;
alter table public.payments add column if not exists payment_provider text default 'lemonsqueezy';
alter table public.payments add column if not exists paid_at timestamptz;
alter table public.payments add column if not exists unlock_status text;
create unique index if not exists idx_payments_payment_id_v142 on public.payments(payment_id);
create index if not exists idx_payments_owner_email_v142 on public.payments(lower(owner_email));
create index if not exists idx_payments_provider_session_v142 on public.payments(provider_session_id);

-- ---------------------------------------------------------------------------
-- Optional workspace/admin tables used by split SaaS admin routes
-- ---------------------------------------------------------------------------
create table if not exists public.checkout_sessions (
  id uuid primary key default gen_random_uuid(),
  checkout_id text unique not null default gen_random_uuid()::text,
  plan_code text,
  project_id text,
  guest_order_id text,
  user_id text,
  owner_email text,
  customer_email text,
  provider_checkout_session_id text,
  checkout_url text,
  status text default 'created',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.guest_orders (
  id uuid primary key default gen_random_uuid(),
  guest_order_id text unique not null default gen_random_uuid()::text,
  email text not null,
  owner_email text,
  project_id text,
  provider_checkout_session_id text,
  payment_status text default 'pending',
  result_token text unique not null default gen_random_uuid()::text,
  guest_token text,
  result_expires_at timestamptz,
  status text default 'draft',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.subscription_usage (
  id uuid primary key default gen_random_uuid(),
  usage_id text unique default gen_random_uuid()::text,
  subscription_id text,
  credit_id text,
  user_id text,
  owner_email text,
  project_id text,
  analysis_id text,
  period_start timestamptz,
  period_end timestamptz,
  analyses_used integer default 0,
  analyses_limit integer default 0,
  used integer default 1,
  created_at timestamptz default now()
);


-- Ensure optional tables upgraded from v1.3.x also have the v1.4.2 columns.
alter table public.checkout_sessions add column if not exists owner_email text;
alter table public.checkout_sessions add column if not exists customer_email text;
alter table public.checkout_sessions add column if not exists provider_checkout_session_id text;
alter table public.checkout_sessions add column if not exists checkout_url text;
alter table public.checkout_sessions add column if not exists status text default 'created';
alter table public.checkout_sessions add column if not exists updated_at timestamptz default now();

alter table public.guest_orders add column if not exists owner_email text;
alter table public.guest_orders add column if not exists guest_token text;
alter table public.guest_orders add column if not exists result_token text default gen_random_uuid()::text;
alter table public.guest_orders add column if not exists result_expires_at timestamptz;
alter table public.guest_orders add column if not exists status text default 'draft';
alter table public.guest_orders add column if not exists updated_at timestamptz default now();

alter table public.subscription_usage add column if not exists usage_id text default gen_random_uuid()::text;
alter table public.subscription_usage add column if not exists credit_id text;
alter table public.subscription_usage add column if not exists owner_email text;
alter table public.subscription_usage add column if not exists project_id text;
alter table public.subscription_usage add column if not exists analysis_id text;
alter table public.subscription_usage add column if not exists analyses_used integer default 0;
alter table public.subscription_usage add column if not exists analyses_limit integer default 0;
alter table public.subscription_usage add column if not exists used integer default 1;

create index if not exists idx_checkout_sessions_owner_v142 on public.checkout_sessions(lower(owner_email));
create index if not exists idx_guest_orders_result_token_v142 on public.guest_orders(result_token);
create index if not exists idx_guest_orders_owner_v142 on public.guest_orders(lower(owner_email));
create index if not exists idx_subscription_usage_owner_v142 on public.subscription_usage(lower(owner_email));

-- ---------------------------------------------------------------------------
-- RLS policies for optional tables. Service-role backend bypasses these, but
-- the anon/authenticated clients remain protected if queried directly.
-- ---------------------------------------------------------------------------
alter table public.checkout_sessions enable row level security;
alter table public.guest_orders enable row level security;
alter table public.subscription_usage enable row level security;

drop policy if exists checkout_sessions_owner_or_staff_v142 on public.checkout_sessions;
create policy checkout_sessions_owner_or_staff_v142 on public.checkout_sessions
for all using (public.is_admin_user() or public.user_matches(owner_email))
with check (public.is_admin_user() or public.user_matches(owner_email));

drop policy if exists guest_orders_staff_only_v142 on public.guest_orders;
create policy guest_orders_staff_only_v142 on public.guest_orders
for all using (public.is_admin_user())
with check (public.is_admin_user());

drop policy if exists subscription_usage_owner_or_staff_v142 on public.subscription_usage;
create policy subscription_usage_owner_or_staff_v142 on public.subscription_usage
for all using (public.is_admin_user() or public.user_matches(owner_email))
with check (public.is_admin_user() or public.user_matches(owner_email));
