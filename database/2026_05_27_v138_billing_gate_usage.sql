-- DevBareun v1.3.8 Billing Gate + Usage Entitlements

alter table if exists analysis_results
  add column if not exists owner_email text,
  add column if not exists dashboard jsonb default '{}'::jsonb,
  add column if not exists kpis jsonb default '{}'::jsonb,
  add column if not exists report_payload jsonb default '{}'::jsonb,
  add column if not exists created_at_ts bigint;

alter table if exists analysis_credits
  add column if not exists owner_email text,
  add column if not exists project_id text,
  add column if not exists plan_code text,
  add column if not exists period_start date,
  add column if not exists period_end date;

alter table if exists subscriptions
  add column if not exists owner_email text,
  add column if not exists monthly_credits integer default 0;

alter table if exists payments
  add column if not exists owner_email text,
  add column if not exists project_id text,
  add column if not exists plan_code text,
  add column if not exists checkout_id text,
  add column if not exists paid_at timestamptz;

alter table if exists subscription_usage
  add column if not exists usage_id text unique,
  add column if not exists credit_id text,
  add column if not exists analysis_id text,
  add column if not exists owner_email text,
  add column if not exists project_id text,
  add column if not exists used integer default 1;

create table if not exists public.workspace_usage_events (
  id uuid primary key default uuid_generate_v4(),
  owner_email text not null,
  event_type text not null,
  project_id text,
  analysis_id text,
  report_id text,
  plan_code text,
  credits_remaining integer,
  payload jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_analysis_results_owner_email on analysis_results(owner_email);
create index if not exists idx_analysis_credits_owner_email on analysis_credits(owner_email);
create index if not exists idx_subscriptions_owner_email on subscriptions(owner_email);
create index if not exists idx_payments_owner_email on payments(owner_email);
create index if not exists idx_workspace_usage_owner_email on workspace_usage_events(owner_email);
