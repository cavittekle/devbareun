-- DevBareun v1.4.30: privacy request workflow and soft-delete retention metadata.
-- Apply after v1.4.25. This migration creates auditable request/review state;
-- it intentionally does not automate physical deletion of files, billing data,
-- immutable audit records, backups or Supabase Auth identities.

create table if not exists public.data_lifecycle_requests (
  id uuid primary key default gen_random_uuid(),
  lifecycle_request_id text unique not null default gen_random_uuid()::text,
  requester_user_id uuid,
  requester_email text not null,
  request_type text not null,
  scope text not null default 'account',
  project_id text,
  reason text,
  status text not null default 'requested',
  requested_at timestamptz not null default now(),
  request_expires_at timestamptz,
  grace_expires_at timestamptz,
  scheduled_purge_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by text,
  review_note text,
  completed_at timestamptz,
  cancelled_at timestamptz,
  cancel_reason text,
  request_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint data_lifecycle_request_type_v1430 check (request_type in ('export', 'erasure')),
  constraint data_lifecycle_scope_v1430 check (scope in ('account', 'project')),
  constraint data_lifecycle_status_v1430 check (status in ('requested', 'in_review', 'approved', 'rejected', 'cancelled', 'completed')),
  constraint data_lifecycle_project_scope_v1430 check (
    (scope = 'account' and project_id is null) or
    (scope = 'project' and project_id is not null)
  ),
  constraint data_lifecycle_export_deadline_v1430 check (
    request_type <> 'export' or request_expires_at is not null
  ),
  constraint data_lifecycle_erasure_grace_v1430 check (
    request_type <> 'erasure' or grace_expires_at is not null
  )
);

create index if not exists idx_data_lifecycle_requester_status_v1430
  on public.data_lifecycle_requests(lower(requester_email), status, requested_at desc);
create index if not exists idx_data_lifecycle_review_queue_v1430
  on public.data_lifecycle_requests(status, requested_at asc)
  where status in ('requested', 'in_review', 'approved');
create index if not exists idx_data_lifecycle_scheduled_purge_v1430
  on public.data_lifecycle_requests(scheduled_purge_at asc)
  where scheduled_purge_at is not null and status = 'approved';

-- Existing delete endpoints use a reversible soft-delete state. The later
-- physical purge runner must act only after reviewed policy checks.
alter table public.projects add column if not exists deleted_at timestamptz;
alter table public.projects add column if not exists purge_after_at timestamptz;
alter table public.projects add column if not exists retention_status text not null default 'active';
alter table public.uploaded_files add column if not exists purge_after_at timestamptz;
alter table public.uploaded_files add column if not exists retention_status text not null default 'active';
alter table public.analysis_results add column if not exists deleted_at timestamptz;
alter table public.analysis_results add column if not exists purge_after_at timestamptz;
alter table public.analysis_results add column if not exists retention_status text not null default 'active';
alter table public.reports add column if not exists deleted_at timestamptz;
alter table public.reports add column if not exists purge_after_at timestamptz;
alter table public.reports add column if not exists retention_status text not null default 'active';

create index if not exists idx_projects_purge_after_v1430
  on public.projects(purge_after_at asc) where purge_after_at is not null;
create index if not exists idx_uploaded_files_purge_after_v1430
  on public.uploaded_files(purge_after_at asc) where purge_after_at is not null;
create index if not exists idx_analysis_results_purge_after_v1430
  on public.analysis_results(purge_after_at asc) where purge_after_at is not null;
create index if not exists idx_reports_purge_after_v1430
  on public.reports(purge_after_at asc) where purge_after_at is not null;

alter table public.data_lifecycle_requests enable row level security;
drop policy if exists data_lifecycle_requests_no_direct_browser_access_v1430 on public.data_lifecycle_requests;
create policy data_lifecycle_requests_no_direct_browser_access_v1430
  on public.data_lifecycle_requests
  for all
  to authenticated
  using (false)
  with check (false);

-- Identity, original scope and requester cannot be rewritten. Review state is
-- mutable only for the controlled API/service-role workflow. Terminal states
-- never reopen silently; an explicit new request is required.
create or replace function public.guard_data_lifecycle_request_v1430()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.lifecycle_request_id is distinct from old.lifecycle_request_id
     or new.requester_user_id is distinct from old.requester_user_id
     or new.requester_email is distinct from old.requester_email
     or new.request_type is distinct from old.request_type
     or new.scope is distinct from old.scope
     or new.project_id is distinct from old.project_id
     or new.requested_at is distinct from old.requested_at
     or new.request_id is distinct from old.request_id
     or new.created_at is distinct from old.created_at then
    raise exception 'data lifecycle request identity is immutable';
  end if;

  if old.status in ('rejected', 'cancelled', 'completed') and new.status is distinct from old.status then
    raise exception 'terminal data lifecycle requests cannot be reopened';
  end if;

  if old.status = 'requested' and new.status not in ('requested', 'in_review', 'approved', 'rejected', 'cancelled') then
    raise exception 'invalid data lifecycle transition from requested';
  end if;
  if old.status = 'in_review' and new.status not in ('in_review', 'approved', 'rejected', 'cancelled') then
    raise exception 'invalid data lifecycle transition from in_review';
  end if;
  if old.status = 'approved' and new.status not in ('approved', 'cancelled', 'completed') then
    raise exception 'invalid data lifecycle transition from approved';
  end if;

  if new.request_type = 'export' and new.scheduled_purge_at is not null then
    raise exception 'export requests cannot schedule a purge';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists data_lifecycle_requests_guard_v1430 on public.data_lifecycle_requests;
create trigger data_lifecycle_requests_guard_v1430
before update on public.data_lifecycle_requests
for each row execute function public.guard_data_lifecycle_request_v1430();
