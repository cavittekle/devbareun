-- DevBareun v1.4.25: transactional outbox for external audit archiving.
-- Apply after v1.4.24. The outbox snapshots v1 append-only audit events in
-- the same database transaction; an external worker delivers them later.

create table if not exists public.audit_archive_outbox (
  id uuid primary key default gen_random_uuid(),
  archive_id text unique not null default gen_random_uuid()::text,
  audit_id text unique not null references public.audit_logs(audit_id) on delete restrict,
  integrity_version smallint not null,
  previous_event_hash text,
  event_hash text not null,
  payload jsonb not null,
  payload_sha256 text not null,
  status text not null default 'pending',
  attempts integer not null default 0,
  max_attempts smallint not null default 8,
  next_attempt_at timestamptz not null default now(),
  lease_owner text,
  lease_token text,
  lease_expires_at timestamptz,
  last_attempt_at timestamptz,
  delivered_at timestamptz,
  delivery_receipt text,
  last_error text,
  retry_requested_at timestamptz,
  retry_requested_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint audit_archive_outbox_status_v1425 check (status in ('pending', 'delivering', 'retry', 'delivered', 'dead_lettered')),
  constraint audit_archive_outbox_attempts_v1425 check (attempts >= 0 and attempts <= 1000),
  constraint audit_archive_outbox_max_attempts_v1425 check (max_attempts between 1 and 20)
);

create index if not exists idx_audit_archive_outbox_ready_v1425
  on public.audit_archive_outbox(status, next_attempt_at, created_at asc)
  where status in ('pending', 'retry');
create index if not exists idx_audit_archive_outbox_lease_v1425
  on public.audit_archive_outbox(status, lease_expires_at)
  where status = 'delivering';
create index if not exists idx_audit_archive_outbox_delivered_v1425
  on public.audit_archive_outbox(delivered_at desc)
  where delivered_at is not null;

alter table public.audit_archive_outbox enable row level security;
drop policy if exists audit_archive_outbox_no_direct_browser_access_v1425 on public.audit_archive_outbox;
create policy audit_archive_outbox_no_direct_browser_access_v1425
  on public.audit_archive_outbox
  for select
  to authenticated
  using (false);

create table if not exists public.audit_archive_worker_heartbeats (
  worker_id text primary key,
  status text not null default 'online',
  started_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  last_result_at timestamptz,
  processed_events integer not null default 0,
  claimed_events integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.audit_archive_worker_heartbeats enable row level security;
drop policy if exists audit_archive_worker_heartbeats_no_direct_browser_access_v1425 on public.audit_archive_worker_heartbeats;
create policy audit_archive_worker_heartbeats_no_direct_browser_access_v1425
  on public.audit_archive_worker_heartbeats
  for select
  to authenticated
  using (false);

create index if not exists idx_audit_archive_worker_heartbeats_seen_v1425
  on public.audit_archive_worker_heartbeats(last_seen_at desc);

-- Snapshots intentionally exclude raw network fields (IP/user-agent) even
-- though the internal audit table retains bounded request context. The payload
-- has already been metadata-redacted by the backend before audit insertion.
create or replace function public.enqueue_audit_archive_outbox_v1425()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  v_payload jsonb;
begin
  if coalesce(new.integrity_version, 0) <> 1 or new.event_hash is null then
    return new;
  end if;

  v_payload := jsonb_build_object(
    'schema_version', 1,
    'audit_id', new.audit_id,
    'actor_email', new.actor_email,
    'actor_role', new.actor_role,
    'actor_user_id', new.actor_user_id,
    'action', new.action,
    'entity_type', new.entity_type,
    'entity_id', new.entity_id,
    'target_owner_email', new.target_owner_email,
    'metadata', new.metadata,
    'metadata_sha256', new.metadata_sha256,
    'event_category', new.event_category,
    'severity', new.severity,
    'request_id', new.request_id,
    'write_origin', new.write_origin,
    'previous_event_hash', new.previous_event_hash,
    'event_hash', new.event_hash,
    'integrity_version', new.integrity_version,
    'created_at', to_char(new.created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
  );

  insert into public.audit_archive_outbox (
    audit_id, integrity_version, previous_event_hash, event_hash,
    payload, payload_sha256, status, max_attempts, next_attempt_at
  ) values (
    new.audit_id, new.integrity_version, new.previous_event_hash, new.event_hash,
    v_payload, encode(digest(v_payload::text, 'sha256'), 'hex'), 'pending', 8, now()
  ) on conflict (audit_id) do nothing;

  return new;
end;
$$;

drop trigger if exists audit_logs_archive_outbox_v1425 on public.audit_logs;
create trigger audit_logs_archive_outbox_v1425
after insert on public.audit_logs
for each row execute function public.enqueue_audit_archive_outbox_v1425();

-- Snapshot fields may never change after creation. Delivery state and lease
-- metadata remain mutable so retries can be processed without rewriting the
-- immutable audit record payload.
create or replace function public.guard_audit_archive_outbox_snapshot_v1425()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.archive_id is distinct from old.archive_id
     or new.audit_id is distinct from old.audit_id
     or new.integrity_version is distinct from old.integrity_version
     or new.previous_event_hash is distinct from old.previous_event_hash
     or new.event_hash is distinct from old.event_hash
     or new.payload is distinct from old.payload
     or new.payload_sha256 is distinct from old.payload_sha256
     or new.created_at is distinct from old.created_at then
    raise exception 'audit archive snapshots are immutable';
  end if;
  if old.status = 'delivered' and new.status is distinct from 'delivered' then
    raise exception 'delivered audit archive records cannot be reopened';
  end if;
  return new;
end;
$$;

drop trigger if exists audit_archive_outbox_immutable_v1425 on public.audit_archive_outbox;
create trigger audit_archive_outbox_immutable_v1425
before update on public.audit_archive_outbox
for each row execute function public.guard_audit_archive_outbox_snapshot_v1425();

create or replace function public.claim_audit_archive_outbox(
  p_worker_id text,
  p_limit integer default 25,
  p_lease_seconds integer default 90
)
returns setof public.audit_archive_outbox
language plpgsql
security definer
set search_path = public
as $$
declare
  v_limit integer := greatest(1, least(coalesce(p_limit, 25), 100));
  v_lease_seconds integer := greatest(30, least(coalesce(p_lease_seconds, 90), 900));
begin
  if coalesce(trim(p_worker_id), '') = '' then
    raise exception 'worker_id is required';
  end if;

  return query
  with candidates as (
    select id
      from public.audit_archive_outbox
     where (
       status in ('pending', 'retry') and next_attempt_at <= now()
     ) or (
       status = 'delivering' and coalesce(lease_expires_at, now() - interval '1 second') < now()
     )
     order by created_at asc
     limit v_limit
     for update skip locked
  )
  update public.audit_archive_outbox target
     set status = 'delivering',
         attempts = target.attempts + 1,
         lease_owner = left(trim(p_worker_id), 180),
         lease_token = gen_random_uuid()::text,
         lease_expires_at = now() + make_interval(secs => v_lease_seconds),
         last_attempt_at = now(),
         updated_at = now()
    from candidates
   where target.id = candidates.id
  returning target.*;
end;
$$;

create or replace function public.record_audit_archive_delivery(
  p_archive_id text,
  p_lease_token text,
  p_receipt text default null
)
returns public.audit_archive_outbox
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.audit_archive_outbox;
begin
  update public.audit_archive_outbox
     set status = 'delivered',
         delivered_at = now(),
         delivery_receipt = nullif(left(coalesce(p_receipt, ''), 240), ''),
         lease_owner = null,
         lease_token = null,
         lease_expires_at = null,
         last_error = null,
         updated_at = now()
   where archive_id = p_archive_id
     and status = 'delivering'
     and lease_token = p_lease_token
  returning * into v_row;

  if v_row.archive_id is null then
    raise exception 'audit archive delivery lease was not found or expired';
  end if;
  return v_row;
end;
$$;

create or replace function public.record_audit_archive_failure(
  p_archive_id text,
  p_lease_token text,
  p_error text,
  p_retry_after_seconds integer default 30,
  p_max_attempts integer default 8
)
returns public.audit_archive_outbox
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.audit_archive_outbox;
  v_max integer := greatest(1, least(coalesce(p_max_attempts, 8), 20));
  v_delay integer := greatest(1, least(coalesce(p_retry_after_seconds, 30), 1800));
begin
  update public.audit_archive_outbox
     set max_attempts = v_max,
         status = case when attempts >= v_max then 'dead_lettered' else 'retry' end,
         next_attempt_at = case when attempts >= v_max then next_attempt_at else now() + make_interval(secs => v_delay) end,
         lease_owner = null,
         lease_token = null,
         lease_expires_at = null,
         last_error = nullif(left(coalesce(p_error, ''), 1200), ''),
         updated_at = now()
   where archive_id = p_archive_id
     and status = 'delivering'
     and lease_token = p_lease_token
  returning * into v_row;

  if v_row.archive_id is null then
    raise exception 'audit archive failure lease was not found or expired';
  end if;
  return v_row;
end;
$$;

create or replace function public.retry_audit_archive_item(
  p_archive_id text,
  p_reset_attempts boolean default false,
  p_requested_by text default null
)
returns public.audit_archive_outbox
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.audit_archive_outbox;
begin
  select * into v_row
    from public.audit_archive_outbox
   where archive_id = p_archive_id
   for update;
  if v_row.archive_id is null then
    raise exception 'audit archive item not found';
  end if;
  if v_row.status = 'delivered' then
    raise exception 'delivered audit archive item cannot be retried';
  end if;
  if v_row.status = 'delivering' then
    raise exception 'audit archive item is currently leased by a worker';
  end if;
  if v_row.status = 'dead_lettered' and not coalesce(p_reset_attempts, false) then
    raise exception 'dead-lettered audit archive item requires reset_attempts=true';
  end if;

  update public.audit_archive_outbox
     set status = 'pending',
         attempts = case when coalesce(p_reset_attempts, false) then 0 else attempts end,
         next_attempt_at = now(),
         lease_owner = null,
         lease_token = null,
         lease_expires_at = null,
         retry_requested_at = now(),
         retry_requested_by = nullif(left(coalesce(p_requested_by, ''), 320), ''),
         updated_at = now()
   where archive_id = p_archive_id
  returning * into v_row;
  return v_row;
end;
$$;

create or replace function public.audit_archive_status(p_limit integer default 100)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_limit integer := greatest(1, least(coalesce(p_limit, 100), 1000));
  v_oldest_pending timestamptz;
  v_last_delivered timestamptz;
  v_recent_dead_letter jsonb;
begin
  select min(created_at) filter (where status in ('pending', 'retry')),
         max(delivered_at)
    into v_oldest_pending, v_last_delivered
    from public.audit_archive_outbox;

  select coalesce(jsonb_agg(item), '[]'::jsonb) into v_recent_dead_letter
    from (
      select jsonb_build_object(
        'archive_id', archive_id,
        'audit_id', audit_id,
        'attempts', attempts,
        'max_attempts', max_attempts,
        'last_error', last_error,
        'created_at', created_at,
        'updated_at', updated_at
      ) as item
      from public.audit_archive_outbox
      where status = 'dead_lettered'
      order by updated_at desc
      limit v_limit
    ) rows;

  return jsonb_build_object(
    'available', true,
    'pending', (select count(*) from public.audit_archive_outbox where status = 'pending'),
    'retry', (select count(*) from public.audit_archive_outbox where status = 'retry'),
    'delivering', (select count(*) from public.audit_archive_outbox where status = 'delivering'),
    'delivered', (select count(*) from public.audit_archive_outbox where status = 'delivered'),
    'dead_lettered', (select count(*) from public.audit_archive_outbox where status = 'dead_lettered'),
    'oldest_pending_at', v_oldest_pending,
    'last_delivered_at', v_last_delivered,
    'recent_dead_lettered', v_recent_dead_letter
  );
end;
$$;

revoke all on function public.claim_audit_archive_outbox(text, integer, integer) from public, anon, authenticated;
revoke all on function public.record_audit_archive_delivery(text, text, text) from public, anon, authenticated;
revoke all on function public.record_audit_archive_failure(text, text, text, integer, integer) from public, anon, authenticated;
revoke all on function public.retry_audit_archive_item(text, boolean, text) from public, anon, authenticated;
revoke all on function public.audit_archive_status(integer) from public, anon, authenticated;
grant execute on function public.claim_audit_archive_outbox(text, integer, integer) to service_role;
grant execute on function public.record_audit_archive_delivery(text, text, text) to service_role;
grant execute on function public.record_audit_archive_failure(text, text, text, integer, integer) to service_role;
grant execute on function public.retry_audit_archive_item(text, boolean, text) to service_role;
grant execute on function public.audit_archive_status(integer) to service_role;
