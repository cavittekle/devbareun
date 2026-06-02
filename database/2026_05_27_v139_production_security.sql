-- DevBareun v1.3.9 — Production Security
-- Apply after v1.3.8 Admin Panel migration.
-- Goal: strict RLS, admin role hardening, protected file access, secure guest expiry.

create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------------
-- User/admin metadata hardening
-- ---------------------------------------------------------------------------
alter table public.users
  add column if not exists auth_user_id uuid,
  add column if not exists is_admin boolean not null default false,
  add column if not exists last_login_at timestamptz;

create index if not exists idx_users_auth_user_id on public.users(auth_user_id);
create index if not exists idx_users_company_id on public.users(company_id);
create index if not exists idx_users_is_admin on public.users(is_admin);

-- ---------------------------------------------------------------------------
-- Ownership columns required by RLS checks
-- ---------------------------------------------------------------------------
alter table public.projects
  add column if not exists owner_email text,
  add column if not exists access_status text default 'active';

alter table public.uploaded_files
  add column if not exists owner_email text,
  add column if not exists size_bytes bigint,
  add column if not exists content_type text,
  add column if not exists failure_reason text,
  add column if not exists error_message text;

alter table public.analysis_results
  add column if not exists owner_email text,
  add column if not exists package_name text,
  add column if not exists created_at_ts bigint;

alter table public.reports
  add column if not exists owner_email text,
  add column if not exists status text default 'ready',
  add column if not exists payload_json jsonb default '{}'::jsonb;

alter table public.guest_orders
  add column if not exists guest_token text,
  add column if not exists expires_at_ts bigint,
  add column if not exists payload_json jsonb default '{}'::jsonb,
  add column if not exists consumed_at timestamptz;

create index if not exists idx_projects_owner_email on public.projects(lower(owner_email));
create index if not exists idx_uploaded_files_owner_email on public.uploaded_files(lower(owner_email));
create index if not exists idx_uploaded_files_storage_path on public.uploaded_files(storage_path);
create index if not exists idx_analysis_owner_email on public.analysis_results(lower(owner_email));
create index if not exists idx_reports_owner_email on public.reports(lower(owner_email));
create index if not exists idx_guest_orders_token on public.guest_orders(result_token);
create index if not exists idx_guest_orders_guest_token on public.guest_orders(guest_token);
create index if not exists idx_guest_orders_expiry on public.guest_orders(result_expires_at);

-- ---------------------------------------------------------------------------
-- Helper functions used by RLS policies
-- ---------------------------------------------------------------------------
create or replace function public.current_user_email()
returns text
language sql
stable
as $$
  select lower(coalesce(auth.jwt() ->> 'email', ''));
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
    from public.users u
    where u.auth_user_id = auth.uid()
      and coalesce(u.is_admin, false) = true
      and coalesce(u.status, 'active') = 'active'
  );
$$;

create or replace function public.owns_project(p_project_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.projects p
    left join public.users u on u.user_id = p.owner_user_id or u.company_id = p.company_id
    where p.project_id = p_project_id
      and (
        u.auth_user_id = auth.uid()
        or lower(coalesce(p.owner_email, '')) = public.current_user_email()
      )
  );
$$;

-- ---------------------------------------------------------------------------
-- Enable RLS on all SaaS tables
-- ---------------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.companies enable row level security;
alter table public.projects enable row level security;
alter table public.uploaded_files enable row level security;
alter table public.analysis_results enable row level security;
alter table public.reports enable row level security;
alter table public.guest_orders enable row level security;
alter table public.subscriptions enable row level security;
alter table public.payments enable row level security;
alter table public.checkout_sessions enable row level security;
alter table public.analysis_credits enable row level security;
alter table public.subscription_usage enable row level security;
alter table public.activity_logs enable row level security;

-- ---------------------------------------------------------------------------
-- Drop old permissive policies if they exist; recreate strict set.
-- ---------------------------------------------------------------------------
drop policy if exists users_read_own_profile on public.users;
drop policy if exists projects_read_own_company on public.projects;
drop policy if exists files_read_own_project on public.uploaded_files;
drop policy if exists analysis_read_own_project on public.analysis_results;
drop policy if exists reports_read_own_project on public.reports;

-- v1.3.9 policy names (idempotent re-run safety)
drop policy if exists users_select_own_or_admin on public.users;
drop policy if exists users_update_own_non_admin on public.users;
drop policy if exists companies_select_member_or_admin on public.companies;
drop policy if exists projects_select_owner_or_admin on public.projects;
drop policy if exists projects_insert_authenticated on public.projects;
drop policy if exists projects_update_owner_or_admin on public.projects;
drop policy if exists uploaded_files_select_owner_or_admin on public.uploaded_files;
drop policy if exists uploaded_files_insert_owner on public.uploaded_files;
drop policy if exists uploaded_files_update_owner_or_admin on public.uploaded_files;
drop policy if exists analysis_select_owner_or_admin on public.analysis_results;
drop policy if exists analysis_insert_owner on public.analysis_results;
drop policy if exists reports_select_owner_or_admin on public.reports;
drop policy if exists payments_select_owner_or_admin on public.payments;
drop policy if exists checkout_sessions_select_owner_or_admin on public.checkout_sessions;
drop policy if exists credits_select_owner_or_admin on public.analysis_credits;
drop policy if exists usage_select_owner_or_admin on public.subscription_usage;
drop policy if exists activity_logs_admin_only on public.activity_logs;
drop policy if exists guest_orders_admin_only on public.guest_orders;

create policy users_select_own_or_admin on public.users
for select using (auth.uid() = auth_user_id or public.is_admin_user());

create policy users_update_own_non_admin on public.users
for update using (auth.uid() = auth_user_id)
with check (auth.uid() = auth_user_id and coalesce(is_admin, false) = false);

create policy companies_select_member_or_admin on public.companies
for select using (
  public.is_admin_user()
  or company_id in (select company_id from public.users where auth_user_id = auth.uid())
);

create policy projects_select_owner_or_admin on public.projects
for select using (public.is_admin_user() or public.owns_project(project_id));

create policy projects_insert_authenticated on public.projects
for insert with check (auth.uid() is not null);

create policy projects_update_owner_or_admin on public.projects
for update using (public.is_admin_user() or public.owns_project(project_id))
with check (public.is_admin_user() or public.owns_project(project_id));

create policy uploaded_files_select_owner_or_admin on public.uploaded_files
for select using (public.is_admin_user() or public.owns_project(project_id));

create policy uploaded_files_insert_owner on public.uploaded_files
for insert with check (auth.uid() is not null and public.owns_project(project_id));

create policy uploaded_files_update_owner_or_admin on public.uploaded_files
for update using (public.is_admin_user() or public.owns_project(project_id))
with check (public.is_admin_user() or public.owns_project(project_id));

create policy analysis_select_owner_or_admin on public.analysis_results
for select using (public.is_admin_user() or public.owns_project(project_id));

create policy analysis_insert_owner on public.analysis_results
for insert with check (auth.uid() is not null and public.owns_project(project_id));

create policy reports_select_owner_or_admin on public.reports
for select using (public.is_admin_user() or public.owns_project(project_id));

create policy payments_select_owner_or_admin on public.payments
for select using (
  public.is_admin_user()
  or lower(coalesce((select email from public.users where user_id = payments.user_id), '')) = public.current_user_email()
);

create policy checkout_sessions_select_owner_or_admin on public.checkout_sessions
for select using (
  public.is_admin_user()
  or lower(coalesce((select email from public.users where user_id = checkout_sessions.user_id), '')) = public.current_user_email()
);

create policy credits_select_owner_or_admin on public.analysis_credits
for select using (
  public.is_admin_user()
  or user_id in (select user_id from public.users where auth_user_id = auth.uid())
  or company_id in (select company_id from public.users where auth_user_id = auth.uid())
);

create policy usage_select_owner_or_admin on public.subscription_usage
for select using (
  public.is_admin_user()
  or user_id in (select user_id from public.users where auth_user_id = auth.uid())
);

create policy activity_logs_admin_only on public.activity_logs
for select using (public.is_admin_user());

-- Guest result rows must never be directly readable by anonymous clients.
-- Backend validates the random token + expiry and serves only a sanitized payload.
create policy guest_orders_admin_only on public.guest_orders
for select using (public.is_admin_user());

-- ---------------------------------------------------------------------------
-- Storage hardening notes
-- ---------------------------------------------------------------------------
-- Supabase Storage bucket must be PRIVATE, not public.
-- Recommended bucket name: devbareun-project-files
-- File download must use /api/storage/create-download-url only.
-- Do not expose storage_path directly to browser code without backend ownership checks.
