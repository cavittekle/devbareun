-- DevBareun v1.4.18 analysis-start idempotency and atomic usage accounting.
-- Run after 2026_06_19_v1417_analysis_job_recovery.sql.
-- Additive/idempotent. The RPC executes subscription/credit consumption once per job.

alter table public.analysis_jobs add column if not exists idempotency_key text;
alter table public.analysis_jobs add column if not exists request_fingerprint text;
alter table public.analysis_jobs add column if not exists billing_status text not null default 'pending';
alter table public.analysis_jobs add column if not exists billing_consumed_at timestamptz;

create unique index if not exists idx_analysis_jobs_owner_idempotency_v1418
  on public.analysis_jobs(lower(owner_email), idempotency_key)
  where idempotency_key is not null;

-- Existing databases can contain historical duplicate active rows, so a
-- partial UNIQUE index would make this additive migration fail. A trigger with
-- a transaction advisory lock prevents new parallel jobs without rewriting
-- legacy rows.
create index if not exists idx_analysis_jobs_active_lookup_v1418
  on public.analysis_jobs(project_id, status, created_at desc);

create or replace function public.prevent_parallel_active_analysis_jobs()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status in ('queued', 'running') then
    perform pg_advisory_xact_lock(hashtext(new.project_id::text));
    if exists (
      select 1 from public.analysis_jobs current
      where current.project_id = new.project_id
        and current.id <> new.id
        and current.status in ('queued', 'running')
    ) then
      raise exception 'An active analysis job already exists for this project'
        using errcode = '23505';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_prevent_parallel_active_analysis_jobs on public.analysis_jobs;
create trigger trg_prevent_parallel_active_analysis_jobs
before insert or update of status, project_id on public.analysis_jobs
for each row execute function public.prevent_parallel_active_analysis_jobs();

create table if not exists public.analysis_usage_ledger (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null unique references public.analysis_jobs(id) on delete cascade,
  user_id uuid,
  owner_email text not null,
  project_id uuid,
  usage_mode text not null,
  subscription_id uuid,
  credit_id uuid,
  created_at timestamptz not null default now()
);

create index if not exists idx_analysis_usage_ledger_owner_v1418
  on public.analysis_usage_ledger(lower(owner_email), created_at desc);

alter table public.analysis_usage_ledger enable row level security;
drop policy if exists "analysis usage ledger service role only" on public.analysis_usage_ledger;
create policy "analysis usage ledger service role only"
  on public.analysis_usage_ledger for all to service_role
  using (true) with check (true);

create or replace function public.consume_analysis_usage_once(
  p_job_id uuid,
  p_owner_email text,
  p_is_unlimited boolean default false
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_job public.analysis_jobs%rowtype;
  v_existing public.analysis_usage_ledger%rowtype;
  v_subscription public.subscriptions%rowtype;
  v_credit public.analysis_credits%rowtype;
  v_ledger_id uuid;
  v_remaining integer;
  v_total integer;
  v_used integer;
begin
  select * into v_job from public.analysis_jobs where id = p_job_id for update;
  if not found then
    return jsonb_build_object('consumed', false, 'error', 'job_not_found');
  end if;

  select * into v_existing from public.analysis_usage_ledger where job_id = p_job_id;
  if found then
    return jsonb_build_object(
      'consumed', false,
      'already_consumed', true,
      'mode', v_existing.usage_mode,
      'ledger_id', v_existing.id
    );
  end if;

  if p_is_unlimited then
    insert into public.analysis_usage_ledger(job_id, user_id, owner_email, project_id, usage_mode)
    values (p_job_id, v_job.user_id, coalesce(p_owner_email, v_job.owner_email), v_job.project_id, 'admin_unlimited')
    returning id into v_ledger_id;
    update public.analysis_jobs
      set billing_status = 'admin_unlimited', billing_consumed_at = now(), updated_at = now()
      where id = p_job_id;
    return jsonb_build_object('consumed', false, 'already_consumed', false, 'mode', 'admin_unlimited', 'ledger_id', v_ledger_id);
  end if;

  select * into v_subscription
    from public.subscriptions
    where lower(owner_email) = lower(coalesce(p_owner_email, v_job.owner_email))
      and lower(coalesce(status, '')) in ('active', 'trialing')
      and coalesce(monthly_project_limit, 0) > coalesce(used_project_count, 0)
    order by updated_at desc nulls last, created_at desc nulls last
    limit 1 for update skip locked;

  if found then
    update public.subscriptions
      set used_project_count = coalesce(used_project_count, 0) + 1, updated_at = now()
      where id = v_subscription.id;
    insert into public.analysis_usage_ledger(job_id, user_id, owner_email, project_id, usage_mode, subscription_id)
    values (p_job_id, v_job.user_id, coalesce(p_owner_email, v_job.owner_email), v_job.project_id, 'subscription', v_subscription.id)
    returning id into v_ledger_id;
    update public.analysis_jobs
      set billing_status = 'consumed', billing_consumed_at = now(), updated_at = now()
      where id = p_job_id;
    return jsonb_build_object('consumed', true, 'already_consumed', false, 'mode', 'subscription', 'ledger_id', v_ledger_id);
  end if;

  select * into v_credit
    from public.analysis_credits
    where lower(owner_email) = lower(coalesce(p_owner_email, v_job.owner_email))
      and lower(coalesce(status, 'active')) = 'active'
      and greatest(coalesce(remaining, 0), coalesce(remaining_credits, 0)) > 0
    order by created_at asc nulls last
    limit 1 for update skip locked;

  if found then
    v_remaining := greatest(coalesce(v_credit.remaining, 0), coalesce(v_credit.remaining_credits, 0));
    v_total := greatest(coalesce(v_credit.total_credits, 0), coalesce(v_credit.amount, 0), v_remaining);
    v_used := least(v_total, coalesce(v_credit.used_credits, 0) + 1);
    update public.analysis_credits
      set remaining = greatest(0, v_remaining - 1),
          remaining_credits = greatest(0, v_remaining - 1),
          total_credits = v_total,
          used_credits = v_used,
          updated_at = now()
      where id = v_credit.id;
    insert into public.analysis_usage_ledger(job_id, user_id, owner_email, project_id, usage_mode, credit_id)
    values (p_job_id, v_job.user_id, coalesce(p_owner_email, v_job.owner_email), v_job.project_id, 'credit', v_credit.id)
    returning id into v_ledger_id;
    update public.analysis_jobs
      set billing_status = 'consumed', billing_consumed_at = now(), updated_at = now()
      where id = p_job_id;
    return jsonb_build_object('consumed', true, 'already_consumed', false, 'mode', 'credit', 'ledger_id', v_ledger_id);
  end if;

  return jsonb_build_object('consumed', false, 'error', 'payment_required');
end;
$$;

revoke all on function public.consume_analysis_usage_once(uuid, text, boolean) from public;
grant execute on function public.consume_analysis_usage_once(uuid, text, boolean) to service_role;
