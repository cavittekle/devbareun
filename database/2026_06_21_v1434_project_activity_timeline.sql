-- DevBareun v1.4.34 — Project Activity Timeline
--
-- Project-visible events are separate from the global immutable audit chain.
-- They contain collaboration-safe metadata and are readable only by the
-- project owner or an explicit active project access grant.

create extension if not exists pgcrypto;

create table if not exists public.project_activity_events (
  id uuid primary key default gen_random_uuid(),
  event_id text unique not null default gen_random_uuid()::text,
  project_id uuid not null references public.projects(id) on delete cascade,
  company_id uuid references public.companies(id) on delete set null,
  actor_user_id uuid references public.users_profile(id) on delete set null,
  actor_email text,
  actor_type text not null default 'user' check (actor_type in ('user', 'system')),
  action text not null,
  entity_type text not null default 'project',
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  metadata_sha256 text not null,
  visibility text not null default 'project' check (visibility = 'project'),
  schema_version text not null default 'v1',
  created_at timestamptz not null default now()
);

alter table public.project_activity_events add column if not exists event_id text default gen_random_uuid()::text;
alter table public.project_activity_events add column if not exists project_id uuid;
alter table public.project_activity_events add column if not exists company_id uuid;
alter table public.project_activity_events add column if not exists actor_user_id uuid;
alter table public.project_activity_events add column if not exists actor_email text;
alter table public.project_activity_events add column if not exists actor_type text default 'user';
alter table public.project_activity_events add column if not exists action text;
alter table public.project_activity_events add column if not exists entity_type text default 'project';
alter table public.project_activity_events add column if not exists entity_id text;
alter table public.project_activity_events add column if not exists metadata jsonb default '{}'::jsonb;
alter table public.project_activity_events add column if not exists metadata_sha256 text;
alter table public.project_activity_events add column if not exists visibility text default 'project';
alter table public.project_activity_events add column if not exists schema_version text default 'v1';
alter table public.project_activity_events add column if not exists created_at timestamptz default now();

create unique index if not exists ux_project_activity_events_event_id_v1434
  on public.project_activity_events(event_id);
create index if not exists idx_project_activity_events_project_created_v1434
  on public.project_activity_events(project_id, created_at desc);
create index if not exists idx_project_activity_events_project_action_v1434
  on public.project_activity_events(project_id, action, created_at desc);

-- Timeline rows are append-only. The backend owns inserts through service-role
-- calls; no browser writes are allowed directly through Supabase.
create or replace function public.reject_project_activity_mutation_v1434()
returns trigger
language plpgsql
as $$
begin
  raise exception 'project activity events are append-only';
end;
$$;

drop trigger if exists project_activity_events_immutable_v1434 on public.project_activity_events;
create trigger project_activity_events_immutable_v1434
before update or delete on public.project_activity_events
for each row execute function public.reject_project_activity_mutation_v1434();

alter table public.project_activity_events enable row level security;

-- Direct reads are constrained to the project owner or an explicit active
-- grant. Same-company membership alone is deliberately insufficient.
drop policy if exists project_activity_events_select_scoped_v1434 on public.project_activity_events;
create policy project_activity_events_select_scoped_v1434 on public.project_activity_events
for select using (
  exists (
    select 1
    from public.users_profile up
    join public.projects p on p.id = project_activity_events.project_id
    left join public.project_access_grants pag
      on pag.project_id = p.id
     and pag.user_id = up.id
     and pag.status = 'active'
    where up.auth_user_id = auth.uid()
      and (
        p.user_id = up.id
        or lower(coalesce(p.owner_email, '')) = lower(coalesce(up.email, ''))
        or pag.id is not null
      )
  )
);
