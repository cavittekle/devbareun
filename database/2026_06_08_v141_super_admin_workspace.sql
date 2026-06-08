-- DevBareun v1.4.1 Super Admin and Workspace Governance
-- Adds scoped staff roles, support/audit/admin-note tables and credit
-- transaction tracking on top of the v1.4.0 production SaaS core.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Users/profile role and status expansion
-- ---------------------------------------------------------------------------
alter table public.users_profile add column if not exists user_id text;
alter table public.users_profile add column if not exists auth_provider text;
alter table public.users_profile add column if not exists company_id uuid;
alter table public.users_profile add column if not exists plan text default 'free';

alter table public.users_profile drop constraint if exists users_profile_role_check;
alter table public.users_profile add constraint users_profile_role_check
check (role in ('user', 'customer', 'admin', 'owner', 'support', 'analyst', 'finance', 'operator'));

alter table public.users_profile drop constraint if exists users_profile_status_check;
alter table public.users_profile add constraint users_profile_status_check
check (status in ('active', 'suspended', 'deactivated'));

create index if not exists idx_users_profile_company_id_v141 on public.users_profile(company_id);
create index if not exists idx_users_profile_plan_v141 on public.users_profile(plan);

-- ---------------------------------------------------------------------------
-- Customer support and internal admin notes
-- ---------------------------------------------------------------------------
create table if not exists public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_id text unique not null default gen_random_uuid()::text,
  owner_email text not null,
  customer_email text not null,
  project_id text,
  subject text not null,
  message text not null,
  status text not null default 'open' check (status in ('open', 'pending', 'resolved')),
  created_by_email text,
  last_internal_note text,
  last_internal_note_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.admin_notes (
  id uuid primary key default gen_random_uuid(),
  note_id text unique not null default gen_random_uuid()::text,
  owner_email text not null,
  customer_email text not null,
  project_id text,
  note text not null,
  created_by_email text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  audit_id text unique not null default gen_random_uuid()::text,
  actor_email text,
  actor_role text,
  action text not null,
  entity_type text,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create table if not exists public.credit_transactions (
  id uuid primary key default gen_random_uuid(),
  transaction_id text unique not null default gen_random_uuid()::text,
  owner_email text not null,
  project_id text,
  amount integer not null,
  reason text not null,
  created_by_email text,
  created_at timestamptz not null default now()
);

create index if not exists idx_support_tickets_owner_v141 on public.support_tickets(lower(owner_email));
create index if not exists idx_support_tickets_status_v141 on public.support_tickets(status);
create index if not exists idx_support_tickets_created_v141 on public.support_tickets(created_at desc);
create index if not exists idx_admin_notes_owner_v141 on public.admin_notes(lower(owner_email));
create index if not exists idx_admin_notes_project_v141 on public.admin_notes(project_id);
create index if not exists idx_audit_logs_actor_v141 on public.audit_logs(lower(actor_email));
create index if not exists idx_audit_logs_created_v141 on public.audit_logs(created_at desc);
create index if not exists idx_credit_transactions_owner_v141 on public.credit_transactions(lower(owner_email));
create index if not exists idx_credit_transactions_created_v141 on public.credit_transactions(created_at desc);

-- Compatibility columns used by the Super Admin read models.
alter table public.activity_logs add column if not exists activity_id text default gen_random_uuid()::text;
alter table public.activity_logs add column if not exists actor text;
alter table public.activity_logs add column if not exists actor_email text;
alter table public.activity_logs add column if not exists event text;
alter table public.activity_logs add column if not exists entity_type text;
alter table public.activity_logs add column if not exists entity_id text;
alter table public.activity_logs add column if not exists payload jsonb default '{}'::jsonb;

alter table public.reports add column if not exists report_id text default gen_random_uuid()::text;
alter table public.reports add column if not exists analysis_id text;
alter table public.reports add column if not exists project_name text;
alter table public.reports add column if not exists analysis_type text;
alter table public.reports add column if not exists print_size text;
alter table public.reports add column if not exists download_count integer default 0;
alter table public.reports add column if not exists unlocked_at timestamptz;

alter table public.payments add column if not exists payment_id text default gen_random_uuid()::text;
alter table public.payments add column if not exists checkout_id text;
alter table public.payments add column if not exists plan_code text;
alter table public.payments add column if not exists project_id text;
alter table public.payments add column if not exists paid_at timestamptz;
alter table public.payments add column if not exists unlock_status text;

alter table public.analysis_credits add column if not exists credit_id text default gen_random_uuid()::text;
alter table public.analysis_credits add column if not exists plan_code text;
alter table public.analysis_credits add column if not exists project_id text;
alter table public.analysis_credits add column if not exists total_credits integer default 0;
alter table public.analysis_credits add column if not exists used_credits integer default 0;
alter table public.analysis_credits add column if not exists remaining_credits integer default 0;
alter table public.analysis_credits add column if not exists status text default 'active';
alter table public.analysis_credits add column if not exists period_start timestamptz;
alter table public.analysis_credits add column if not exists period_end timestamptz;

-- ---------------------------------------------------------------------------
-- RLS helpers and policies
-- ---------------------------------------------------------------------------
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
      and up.role in ('admin', 'owner', 'support', 'analyst', 'finance', 'operator')
      and up.status = 'active'
  );
$$;

alter table public.support_tickets enable row level security;
alter table public.admin_notes enable row level security;
alter table public.audit_logs enable row level security;
alter table public.credit_transactions enable row level security;

drop policy if exists support_tickets_owner_or_staff_v141 on public.support_tickets;
create policy support_tickets_owner_or_staff_v141 on public.support_tickets
for all using (public.is_admin_user() or public.user_matches(owner_email))
with check (public.is_admin_user() or public.user_matches(owner_email));

drop policy if exists admin_notes_staff_only_v141 on public.admin_notes;
create policy admin_notes_staff_only_v141 on public.admin_notes
for all using (public.is_admin_user())
with check (public.is_admin_user());

drop policy if exists audit_logs_staff_only_v141 on public.audit_logs;
create policy audit_logs_staff_only_v141 on public.audit_logs
for all using (public.is_admin_user())
with check (public.is_admin_user());

drop policy if exists credit_transactions_owner_or_staff_v141 on public.credit_transactions;
create policy credit_transactions_owner_or_staff_v141 on public.credit_transactions
for all using (public.is_admin_user() or public.user_matches(owner_email))
with check (public.is_admin_user() or public.user_matches(owner_email));

-- ---------------------------------------------------------------------------
-- First owner setup helper
-- ---------------------------------------------------------------------------
-- After creating the owner in Supabase Auth, run:
-- update public.users_profile
-- set role = 'owner', status = 'active'
-- where lower(email) = lower('owner@devbareun.com');
