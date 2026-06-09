
-- DevBareun v1.3.0 SaaS Foundation Schema
-- PostgreSQL / Supabase

create extension if not exists "uuid-ossp";

create table if not exists public.companies (
  id uuid primary key default uuid_generate_v4(),
  company_id text unique not null,
  company_name text not null,
  contact_person text,
  email text,
  phone text,
  country text,
  subscription_plan text default 'free',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.users (
  id uuid primary key default uuid_generate_v4(),
  user_id text unique not null,
  auth_user_id uuid,
  company_id text references public.companies(company_id),
  email text unique not null,
  role text default 'owner',
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.plans (
  id uuid primary key default uuid_generate_v4(),
  plan_code text unique not null,
  plan_name text not null,
  billing_type text not null,
  monthly_project_credits integer not null default 0,
  pdf_export boolean default true,
  excel_export boolean default false,
  a3_print boolean default false,
  advanced_dashboard boolean default false,
  provider_variant_id text,
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists public.projects (
  id uuid primary key default uuid_generate_v4(),
  project_id text unique not null,
  company_id text references public.companies(company_id),
  owner_user_id text references public.users(user_id),
  guest_order_id text,
  project_name text not null,
  location text,
  contractor text,
  client text,
  start_date date,
  end_date date,
  duration text,
  contract_value numeric,
  currency text default 'AZN',
  project_status text default 'draft',
  analysis_type text default 'all',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.uploaded_files (
  id uuid primary key default uuid_generate_v4(),
  file_id text unique not null,
  project_id text references public.projects(project_id) on delete cascade,
  original_name text not null,
  file_size_bytes bigint,
  mime_type text,
  extension text,
  storage_bucket text,
  storage_path text,
  checksum text,
  status text default 'uploaded',
  uploaded_by_user_id text references public.users(user_id),
  created_at timestamptz default now(),
  deleted_at timestamptz
);

create table if not exists public.analysis_results (
  id uuid primary key default uuid_generate_v4(),
  analysis_id text unique not null,
  project_id text references public.projects(project_id) on delete cascade,
  analysis_type text not null,
  uploaded_file_ids text[] default '{}',
  status text default 'queued',
  result_json jsonb default '{}'::jsonb,
  confidence_score integer,
  risk_level text,
  created_at timestamptz default now(),
  completed_at timestamptz
);

create table if not exists public.reports (
  id uuid primary key default uuid_generate_v4(),
  report_id text unique not null,
  analysis_id text references public.analysis_results(analysis_id) on delete cascade,
  project_id text references public.projects(project_id) on delete cascade,
  report_type text not null,
  language text default 'en',
  storage_bucket text,
  storage_path text,
  created_at timestamptz default now()
);

create table if not exists public.guest_orders (
  id uuid primary key default uuid_generate_v4(),
  guest_order_id text unique not null,
  email text not null,
  project_id text,
  provider_checkout_session_id text,
  payment_status text default 'pending',
  result_token text unique not null,
  result_expires_at timestamptz,
  status text default 'draft',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.subscriptions (
  id uuid primary key default uuid_generate_v4(),
  subscription_id text unique not null,
  user_id text references public.users(user_id),
  company_id text references public.companies(company_id),
  plan_code text references public.plans(plan_code),
  provider text,
  provider_customer_id text,
  provider_subscription_id text,
  status text default 'inactive',
  current_period_start timestamptz,
  current_period_end timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.payments (
  id uuid primary key default uuid_generate_v4(),
  payment_id text unique not null,
  user_id text references public.users(user_id),
  guest_order_id text references public.guest_orders(guest_order_id),
  provider_payment_id text,
  provider_checkout_session_id text,
  amount numeric,
  currency text default 'USD',
  status text default 'pending',
  payment_type text not null,
  created_at timestamptz default now()
);

create table if not exists public.checkout_sessions (
  id uuid primary key default uuid_generate_v4(),
  checkout_id text unique not null,
  plan_code text,
  project_id text,
  guest_order_id text,
  user_id text,
  provider_checkout_session_id text,
  checkout_url text,
  status text default 'created',
  created_at timestamptz default now()
);

create table if not exists public.analysis_credits (
  id uuid primary key default uuid_generate_v4(),
  credit_id text unique not null,
  user_id text references public.users(user_id),
  company_id text references public.companies(company_id),
  guest_order_id text references public.guest_orders(guest_order_id),
  source text not null,
  total_credits integer not null default 0,
  used_credits integer not null default 0,
  remaining_credits integer not null default 0,
  reset_at timestamptz,
  status text default 'active',
  created_at timestamptz default now()
);

create table if not exists public.subscription_usage (
  id uuid primary key default uuid_generate_v4(),
  subscription_id text references public.subscriptions(subscription_id),
  user_id text references public.users(user_id),
  period_start timestamptz,
  period_end timestamptz,
  analyses_used integer default 0,
  analyses_limit integer default 0,
  created_at timestamptz default now()
);

create table if not exists public.activity_logs (
  id uuid primary key default uuid_generate_v4(),
  actor_user_id text,
  actor_email text,
  event text not null,
  entity_type text,
  entity_id text,
  payload jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
