-- DevBareun v1.4.13 Database Contract Bridge
-- Additive/idempotent aliases and timestamp columns used by the cleaned backend
-- and release contract checks. Run after 2026_06_18_v145_analysis_worker.sql.

-- ---------------------------------------------------------------------------
-- Project/public API aliases
-- ---------------------------------------------------------------------------
alter table public.projects add column if not exists name text;
update public.projects
set name = coalesce(name, project_name)
where name is null;

-- ---------------------------------------------------------------------------
-- Billing/report timestamp compatibility
-- ---------------------------------------------------------------------------
alter table public.analysis_credits add column if not exists updated_at timestamptz default now();
alter table public.payments add column if not exists updated_at timestamptz default now();
alter table public.reports add column if not exists updated_at timestamptz default now();
alter table public.risks add column if not exists updated_at timestamptz default now();

-- ---------------------------------------------------------------------------
-- Payment event aliases used by webhook idempotency/read models
-- ---------------------------------------------------------------------------
alter table public.payment_events add column if not exists provider text default 'lemonsqueezy';
alter table public.payment_events add column if not exists event_id text;
alter table public.payment_events add column if not exists created_at timestamptz default now();
update public.payment_events
set event_id = coalesce(event_id, provider_event_id),
    created_at = coalesce(created_at, processed_at)
where event_id is null or created_at is null;
create unique index if not exists idx_payment_events_event_id_v1413 on public.payment_events(event_id) where event_id is not null;

-- ---------------------------------------------------------------------------
-- Super-admin table aliases
-- ---------------------------------------------------------------------------
alter table public.support_tickets add column if not exists priority text default 'normal';

alter table public.admin_notes add column if not exists target_type text default 'customer';
alter table public.admin_notes add column if not exists target_id text;
alter table public.admin_notes add column if not exists created_by text;
update public.admin_notes
set target_id = coalesce(target_id, project_id, owner_email),
    created_by = coalesce(created_by, created_by_email)
where target_id is null or created_by is null;

alter table public.audit_logs add column if not exists target_type text;
alter table public.audit_logs add column if not exists target_id text;
update public.audit_logs
set target_type = coalesce(target_type, entity_type),
    target_id = coalesce(target_id, entity_id)
where target_type is null or target_id is null;

alter table public.credit_transactions add column if not exists created_by text;
update public.credit_transactions
set created_by = coalesce(created_by, created_by_email)
where created_by is null;

-- ---------------------------------------------------------------------------
-- Guest/subscription usage aliases
-- ---------------------------------------------------------------------------
alter table public.guest_orders add column if not exists checkout_id text;
update public.guest_orders
set checkout_id = coalesce(checkout_id, provider_checkout_session_id)
where checkout_id is null;

alter table public.subscription_usage add column if not exists used_credits integer default 0;
alter table public.subscription_usage add column if not exists updated_at timestamptz default now();
update public.subscription_usage
set used_credits = coalesce(nullif(used_credits, 0), analyses_used, used, 0)
where used_credits is null or used_credits = 0;

-- Helpful indexes for newly bridged aliases.
create index if not exists idx_projects_name_v1413 on public.projects(name);
create index if not exists idx_support_tickets_priority_v1413 on public.support_tickets(priority);
create index if not exists idx_admin_notes_target_v1413 on public.admin_notes(target_type, target_id);
create index if not exists idx_audit_logs_target_v1413 on public.audit_logs(target_type, target_id);
create index if not exists idx_guest_orders_checkout_v1413 on public.guest_orders(checkout_id);
