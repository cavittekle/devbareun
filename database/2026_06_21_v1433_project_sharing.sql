-- DevBareun v1.4.33 — Explicit Project Sharing
--
-- Company membership remains insufficient for access. Each non-owner user
-- needs an active project_access_grants record scoped to the project and the
-- same company workspace.

create extension if not exists pgcrypto;

alter table public.projects add column if not exists company_id uuid;

-- Backfill only deterministic profile/company links. Projects with no valid
-- company remain owner-only and cannot be shared until assigned to a workspace.
update public.projects p
set company_id = up.company_id
from public.users_profile up
where p.company_id is null
  and up.company_id is not null
  and (
    p.user_id = up.id
    or (p.owner_email is not null and lower(p.owner_email) = lower(up.email))
  );

create table if not exists public.project_access_grants (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  membership_id uuid not null references public.company_memberships(id) on delete cascade,
  user_id uuid not null references public.users_profile(id) on delete cascade,
  member_email text not null,
  project_role text not null check (project_role in ('manager', 'editor', 'viewer')),
  status text not null default 'active' check (status in ('active', 'revoked')),
  granted_by_user_id uuid references public.users_profile(id) on delete set null,
  granted_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.project_access_grants add column if not exists project_id uuid;
alter table public.project_access_grants add column if not exists company_id uuid;
alter table public.project_access_grants add column if not exists membership_id uuid;
alter table public.project_access_grants add column if not exists user_id uuid;
alter table public.project_access_grants add column if not exists member_email text;
alter table public.project_access_grants add column if not exists project_role text default 'viewer';
alter table public.project_access_grants add column if not exists status text default 'active';
alter table public.project_access_grants add column if not exists granted_by_user_id uuid;
alter table public.project_access_grants add column if not exists granted_at timestamptz default now();
alter table public.project_access_grants add column if not exists created_at timestamptz default now();
alter table public.project_access_grants add column if not exists updated_at timestamptz default now();

create unique index if not exists ux_project_access_grants_project_user_v1433
  on public.project_access_grants (project_id, user_id);
create index if not exists idx_project_access_grants_user_status_v1433
  on public.project_access_grants (user_id, status, project_id);
create index if not exists idx_project_access_grants_project_status_v1433
  on public.project_access_grants (project_id, status, project_role);

-- Database-level tenancy guard: a grant cannot cross companies, point at a
-- suspended/non-matching membership, or represent the project owner.
create or replace function public.validate_project_access_grant_v1433()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  project_company uuid;
  membership_company uuid;
  membership_user uuid;
  membership_status text;
  owner_user uuid;
  owner_email text;
begin
  select company_id, user_id, owner_email
    into project_company, owner_user, owner_email
  from public.projects
  where id = new.project_id;

  if project_company is null or project_company <> new.company_id then
    raise exception 'project access grant company must match project company';
  end if;

  select company_id, user_id, status
    into membership_company, membership_user, membership_status
  from public.company_memberships
  where id = new.membership_id;

  if membership_company is null or membership_company <> new.company_id
     or membership_user is null or membership_user <> new.user_id
     or membership_status <> 'active' then
    raise exception 'project access grant requires an active member of the same company';
  end if;

  if owner_user = new.user_id then
    raise exception 'project owner uses implicit owner access and cannot receive a grant';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_validate_project_access_grant_v1433 on public.project_access_grants;
create trigger trg_validate_project_access_grant_v1433
before insert or update of project_id, company_id, membership_id, user_id, status
on public.project_access_grants
for each row execute function public.validate_project_access_grant_v1433();

alter table public.project_access_grants enable row level security;

-- Direct Supabase access is limited to the caller's own grants. The backend
-- owns grant creation/revocation via capability checks and service-role calls.
drop policy if exists project_access_grants_select_self_v1433 on public.project_access_grants;
create policy project_access_grants_select_self_v1433 on public.project_access_grants
for select using (
  user_id in (select id from public.users_profile where auth_user_id = auth.uid())
);
