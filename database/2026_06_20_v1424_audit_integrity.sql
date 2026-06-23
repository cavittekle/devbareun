-- DevBareun v1.4.24: append-only, tamper-evident audit records.
-- Apply after v1.4.23. This migration is additive and preserves legacy rows.

create extension if not exists pgcrypto;

alter table public.audit_logs
  add column if not exists actor_user_id text,
  add column if not exists target_owner_email text,
  add column if not exists request_id text,
  add column if not exists write_origin text,
  add column if not exists event_category text,
  add column if not exists severity text,
  add column if not exists metadata_sha256 text,
  add column if not exists previous_event_hash text,
  add column if not exists event_hash text,
  add column if not exists integrity_version smallint not null default 0;

alter table public.audit_logs
  drop constraint if exists audit_logs_integrity_version_v1424,
  drop constraint if exists audit_logs_event_category_v1424,
  drop constraint if exists audit_logs_severity_v1424;

alter table public.audit_logs
  add constraint audit_logs_integrity_version_v1424 check (integrity_version in (0, 1)),
  add constraint audit_logs_event_category_v1424 check (event_category is null or event_category in ('read', 'mutation', 'privileged_mutation', 'system')),
  add constraint audit_logs_severity_v1424 check (severity is null or severity in ('info', 'medium', 'high'));

create index if not exists idx_audit_logs_request_v1424
  on public.audit_logs(request_id)
  where request_id is not null;
create index if not exists idx_audit_logs_integrity_v1424
  on public.audit_logs(integrity_version, created_at desc);
create index if not exists idx_audit_logs_target_owner_v1424
  on public.audit_logs(lower(target_owner_email))
  where target_owner_email is not null;

-- New v1 records are created only through this RPC. A transaction-scoped
-- advisory lock serializes the chain so concurrent admin actions cannot fork
-- it. This gives tamper evidence, not external non-repudiation: a database
-- superuser could still replace both rows and hashes.
create or replace function public.append_audit_event(
  p_audit_id text,
  p_actor_email text,
  p_actor_role text,
  p_actor_user_id text,
  p_action text,
  p_entity_type text,
  p_entity_id text,
  p_target_owner_email text,
  p_metadata jsonb default '{}'::jsonb,
  p_metadata_sha256 text default null,
  p_event_category text default 'system',
  p_severity text default 'info',
  p_request_id text default null,
  p_ip_address text default null,
  p_user_agent text default null,
  p_write_origin text default 'api'
)
returns public.audit_logs
language plpgsql
security definer
set search_path = public
as $$
declare
  v_previous_hash text;
  v_metadata jsonb := coalesce(p_metadata, '{}'::jsonb);
  v_metadata_hash text;
  v_created_at timestamptz := clock_timestamp();
  v_created_at_text text;
  v_event_hash text;
  v_row public.audit_logs;
begin
  if coalesce(trim(p_audit_id), '') = '' or coalesce(trim(p_action), '') = '' then
    raise exception 'audit_id and action are required';
  end if;

  perform pg_advisory_xact_lock(hashtext('devbareun.audit.v1424.chain'));

  select event_hash into v_previous_hash
    from public.audit_logs
   where integrity_version = 1
     and event_hash is not null
   order by created_at desc, id desc
   limit 1;

  v_previous_hash := coalesce(v_previous_hash, 'GENESIS_V1424');
  v_metadata_hash := coalesce(nullif(trim(p_metadata_sha256), ''), encode(digest(v_metadata::text, 'sha256'), 'hex'));
  v_created_at_text := to_char(v_created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"');
  v_event_hash := encode(digest(concat_ws('|',
    'v1', p_audit_id, coalesce(p_actor_email, ''), coalesce(p_actor_role, ''),
    coalesce(p_actor_user_id, ''), coalesce(p_action, ''), coalesce(p_entity_type, ''),
    coalesce(p_entity_id, ''), coalesce(p_target_owner_email, ''), v_metadata_hash,
    coalesce(p_event_category, 'system'), coalesce(p_severity, 'info'),
    coalesce(p_request_id, ''), coalesce(p_write_origin, 'api'), v_created_at_text,
    v_previous_hash
  ), 'sha256'), 'hex');

  insert into public.audit_logs (
    audit_id, actor_email, actor_role, actor_user_id, action, entity_type, entity_id,
    target_owner_email, metadata, metadata_sha256, event_category, severity,
    request_id, ip_address, user_agent, write_origin, previous_event_hash, event_hash,
    integrity_version, created_at
  ) values (
    p_audit_id, p_actor_email, p_actor_role, p_actor_user_id, p_action, p_entity_type, p_entity_id,
    p_target_owner_email, v_metadata, v_metadata_hash, coalesce(p_event_category, 'system'), coalesce(p_severity, 'info'),
    p_request_id, p_ip_address, p_user_agent, coalesce(p_write_origin, 'api'), v_previous_hash, v_event_hash,
    1, v_created_at
  ) returning * into v_row;

  return v_row;
end;
$$;

revoke all on function public.append_audit_event(
  text, text, text, text, text, text, text, text, jsonb, text, text, text, text, text, text, text
) from public, anon, authenticated;
grant execute on function public.append_audit_event(
  text, text, text, text, text, text, text, text, jsonb, text, text, text, text, text, text, text
) to service_role;

-- Database-side verification avoids trusting UI-side ordering. ``p_limit`` is
-- intentionally bounded for the operator endpoint; set it high during a
-- deliberate full audit review.
create or replace function public.audit_integrity_status(p_limit integer default 2000)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_previous_hash text := 'GENESIS_V1424';
  v_expected_hash text;
  v_checked integer := 0;
  v_broken_audit_id text := null;
  v_row public.audit_logs;
  v_limit integer := greatest(1, least(coalesce(p_limit, 2000), 10000));
  v_created_at_text text;
begin
  for v_row in
    select *
      from public.audit_logs
     where integrity_version = 1
     order by created_at asc, id asc
     limit v_limit
  loop
    v_checked := v_checked + 1;
    v_created_at_text := to_char(v_row.created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"');
    v_expected_hash := encode(digest(concat_ws('|',
      'v1', v_row.audit_id, coalesce(v_row.actor_email, ''), coalesce(v_row.actor_role, ''),
      coalesce(v_row.actor_user_id, ''), coalesce(v_row.action, ''), coalesce(v_row.entity_type, ''),
      coalesce(v_row.entity_id, ''), coalesce(v_row.target_owner_email, ''), coalesce(v_row.metadata_sha256, ''),
      coalesce(v_row.event_category, 'system'), coalesce(v_row.severity, 'info'),
      coalesce(v_row.request_id, ''), coalesce(v_row.write_origin, 'api'), v_created_at_text,
      v_previous_hash
    ), 'sha256'), 'hex');
    if v_row.previous_event_hash is distinct from v_previous_hash or v_row.event_hash is distinct from v_expected_hash then
      v_broken_audit_id := v_row.audit_id;
      exit;
    end if;
    v_previous_hash := v_row.event_hash;
  end loop;

  return jsonb_build_object(
    'available', true,
    'verified', v_broken_audit_id is null,
    'checked_events', v_checked,
    'checked_limit', v_limit,
    'broken_audit_id', v_broken_audit_id,
    'last_event_hash', case when v_checked > 0 and v_broken_audit_id is null then v_previous_hash else null end,
    'integrity_version', 1
  );
end;
$$;

revoke all on function public.audit_integrity_status(integer) from public, anon, authenticated;
grant execute on function public.audit_integrity_status(integer) to service_role;

-- Audit rows are append-only after this migration. The API writes via the RPC
-- above; any direct mutation or deletion is rejected, including service-role
-- traffic.
create or replace function public.reject_audit_log_mutation_v1424()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception 'audit logs are append-only and cannot be updated or deleted';
end;
$$;

drop trigger if exists audit_logs_immutable_v1424 on public.audit_logs;
create trigger audit_logs_immutable_v1424
before update or delete on public.audit_logs
for each row execute function public.reject_audit_log_mutation_v1424();
