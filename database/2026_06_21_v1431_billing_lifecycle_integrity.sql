-- DevBareun v1.4.31: checkout lifecycle, retry-safe Lemon Squeezy events and subscription period integrity.
-- Additive/idempotent. Apply after v1.4.30 data lifecycle migration.

-- ---------------------------------------------------------------------------
-- Checkout and payment lifecycle metadata
-- ---------------------------------------------------------------------------
alter table public.checkout_sessions add column if not exists provider_order_id text;
alter table public.checkout_sessions add column if not exists last_event_id text;
alter table public.checkout_sessions add column if not exists paid_at timestamptz;
alter table public.checkout_sessions add column if not exists failure_code text;
alter table public.checkout_sessions add column if not exists expires_at timestamptz;
alter table public.checkout_sessions add column if not exists updated_at timestamptz default now();

alter table public.payments add column if not exists provider_order_id text;
alter table public.payments add column if not exists last_provider_event_id text;
alter table public.payments add column if not exists failure_reason_code text;
alter table public.payments add column if not exists refunded_at timestamptz;
alter table public.payments add column if not exists updated_at timestamptz default now();

alter table public.analysis_credits add column if not exists project_id uuid;
alter table public.analysis_credits add column if not exists checkout_id text;
alter table public.analysis_credits add column if not exists provider_order_id text;
alter table public.analysis_credits add column if not exists source_event_id text;
alter table public.analysis_credits add column if not exists updated_at timestamptz default now();

-- Existing rows were written before lifecycle status names existed. Keep their
-- historical meaning but normalize blank values for deterministic filtering.
update public.checkout_sessions
set status = coalesce(nullif(status, ''), 'legacy_unknown'),
    updated_at = coalesce(updated_at, created_at, now())
where status is null or status = '' or updated_at is null;

update public.payments
set status = coalesce(nullif(status, ''), 'legacy_unknown'),
    updated_at = coalesce(updated_at, created_at, now())
where status is null or status = '' or updated_at is null;

create index if not exists idx_checkout_sessions_owner_status_v1431
  on public.checkout_sessions(lower(owner_email), status, updated_at desc);
create index if not exists idx_checkout_sessions_provider_v1431
  on public.checkout_sessions(provider_checkout_session_id);
create index if not exists idx_payments_checkout_v1431
  on public.payments(checkout_id);
create index if not exists idx_payments_provider_order_v1431
  on public.payments(provider_order_id);
create unique index if not exists idx_analysis_credits_source_event_v1431
  on public.analysis_credits(source_event_id)
  where source_event_id is not null;
create index if not exists idx_analysis_credits_provider_order_v1431
  on public.analysis_credits(provider_order_id);

-- ---------------------------------------------------------------------------
-- Payment webhook event state machine
-- ---------------------------------------------------------------------------
alter table public.payment_events add column if not exists provider text default 'lemonsqueezy';
alter table public.payment_events add column if not exists event_id text;
alter table public.payment_events add column if not exists processing_status text default 'received';
alter table public.payment_events add column if not exists attempts integer not null default 0;
alter table public.payment_events add column if not exists max_attempts integer not null default 5;
alter table public.payment_events add column if not exists received_at timestamptz default now();
alter table public.payment_events add column if not exists last_attempt_at timestamptz;
alter table public.payment_events add column if not exists completed_at timestamptz;
alter table public.payment_events add column if not exists last_error_code text;
alter table public.payment_events add column if not exists payload_sha256 text;
alter table public.payment_events add column if not exists checkout_id text;
alter table public.payment_events add column if not exists owner_email text;
alter table public.payment_events add column if not exists plan_name text;
alter table public.payment_events add column if not exists outcome jsonb not null default '{}'::jsonb;
alter table public.payment_events add column if not exists updated_at timestamptz default now();
alter table public.payment_events alter column processed_at drop not null;

update public.payment_events
set provider = coalesce(nullif(provider, ''), 'lemonsqueezy'),
    event_id = coalesce(event_id, provider_event_id),
    processing_status = case
      when coalesce(processing_status, '') in ('received', 'processing', 'processed', 'failed', 'dead_lettered') then processing_status
      else 'processed'
    end,
    completed_at = coalesce(completed_at, processed_at),
    received_at = coalesce(received_at, processed_at, now()),
    updated_at = coalesce(updated_at, processed_at, now())
where provider is null or event_id is null or processing_status is null or received_at is null or updated_at is null;

alter table public.payment_events drop constraint if exists payment_events_processing_status_v1431;
alter table public.payment_events add constraint payment_events_processing_status_v1431
  check (processing_status in ('received', 'processing', 'processed', 'failed', 'dead_lettered'));
alter table public.payment_events drop constraint if exists payment_events_attempts_v1431;
alter table public.payment_events add constraint payment_events_attempts_v1431
  check (attempts >= 0 and max_attempts between 1 and 20);

create index if not exists idx_payment_events_processing_v1431
  on public.payment_events(processing_status, updated_at asc);
create index if not exists idx_payment_events_checkout_v1431
  on public.payment_events(checkout_id);

-- Claim one event atomically. Duplicate delivered events become a no-op only
-- after processing completed; failed events may be retried until the budget is
-- exhausted. The raw provider payload is deliberately not persisted here.
drop function if exists public.claim_payment_webhook_event(text, text, text, jsonb, text, text, text, text, integer);

create or replace function public.claim_payment_webhook_event(
  p_provider_event_id text,
  p_provider text,
  p_event_type text,
  p_payload jsonb,
  p_payload_sha256 text,
  p_checkout_id text default null,
  p_plan_name text default null,
  p_max_attempts integer default 5
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_event public.payment_events%rowtype;
  v_limit integer := greatest(1, least(coalesce(p_max_attempts, 5), 20));
begin
  if nullif(trim(coalesce(p_provider_event_id, '')), '') is null then
    raise exception 'provider event id is required';
  end if;

  insert into public.payment_events(
    provider_event_id, provider, event_id, event_type, payload, payload_sha256,
    checkout_id, plan_name, processing_status, attempts,
    max_attempts, received_at, updated_at
  ) values (
    p_provider_event_id, coalesce(nullif(p_provider, ''), 'lemonsqueezy'),
    p_provider_event_id, p_event_type, coalesce(p_payload, '{}'::jsonb),
    p_payload_sha256, p_checkout_id,
    p_plan_name, 'received', 0, v_limit, now(), now()
  ) on conflict (provider_event_id) do nothing;

  select * into v_event
  from public.payment_events
  where provider_event_id = p_provider_event_id
  for update;

  if v_event.processing_status = 'processed' then
    return jsonb_build_object('claimed', false, 'state', 'duplicate_processed', 'attempts', v_event.attempts);
  end if;

  if v_event.processing_status = 'dead_lettered' or v_event.attempts >= v_event.max_attempts then
    update public.payment_events
    set processing_status = 'dead_lettered', updated_at = now()
    where id = v_event.id;
    return jsonb_build_object('claimed', false, 'state', 'dead_lettered', 'attempts', v_event.attempts);
  end if;

  update public.payment_events
  set processing_status = 'processing',
      attempts = v_event.attempts + 1,
      max_attempts = v_limit,
      last_attempt_at = now(),
      last_error_code = null,
      updated_at = now()
  where id = v_event.id
  returning * into v_event;

  return jsonb_build_object('claimed', true, 'state', 'processing', 'attempts', v_event.attempts);
end;
$$;

create or replace function public.complete_payment_webhook_event(
  p_provider_event_id text,
  p_success boolean,
  p_outcome jsonb default '{}'::jsonb,
  p_error_code text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_event public.payment_events%rowtype;
begin
  select * into v_event
  from public.payment_events
  where provider_event_id = p_provider_event_id
  for update;

  if not found then
    raise exception 'payment event not found';
  end if;

  if v_event.processing_status = 'processed' then
    return jsonb_build_object('updated', false, 'state', 'duplicate_processed');
  end if;

  if p_success then
    update public.payment_events
    set processing_status = 'processed',
        processed_at = now(),
        completed_at = now(),
        outcome = coalesce(p_outcome, '{}'::jsonb),
        last_error_code = null,
        updated_at = now()
    where id = v_event.id;
    return jsonb_build_object('updated', true, 'state', 'processed');
  end if;

  update public.payment_events
  set processing_status = case when attempts >= max_attempts then 'dead_lettered' else 'failed' end,
      outcome = coalesce(p_outcome, '{}'::jsonb),
      last_error_code = nullif(left(coalesce(p_error_code, ''), 80), ''),
      updated_at = now()
  where id = v_event.id
  returning * into v_event;

  return jsonb_build_object('updated', true, 'state', v_event.processing_status, 'attempts', v_event.attempts);
end;
$$;

-- Service-role backend calls the RPCs. Do not broaden browser-access grants.
revoke all on function public.claim_payment_webhook_event(text, text, text, jsonb, text, text, text, integer) from public;
revoke all on function public.complete_payment_webhook_event(text, boolean, jsonb, text) from public;

-- Payment event metadata must remain staff-only when queried directly. The
-- backend stores only a redacted event summary and hash after v1.4.31.
-- The legacy owner_email column is retained for compatibility but is never populated by the v1.4.31 claim RPC.
alter table public.payment_events enable row level security;
