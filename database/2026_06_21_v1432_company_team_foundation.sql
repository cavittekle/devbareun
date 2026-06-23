-- DevBareun v1.4.32 — Company Team Foundation
--
-- Controlled company roster and invitation records. This migration deliberately
-- does NOT alter project/file/report RLS or ownership rules. Company membership
-- does not yet grant cross-user access; project sharing must be added through an
-- explicit project-access migration later.

create extension if not exists pgcrypto;

create table if not exists public.company_memberships (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  user_id uuid references public.users_profile(id) on delete set null,
  member_email text not null,
  company_role text not null default 'viewer' check (company_role in ('owner', 'manager', 'editor', 'viewer')),
  status text not null default 'active' check (status in ('active', 'suspended')),
  invited_by_user_id uuid references public.users_profile(id) on delete set null,
  joined_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.company_memberships add column if not exists company_id uuid;
alter table public.company_memberships add column if not exists user_id uuid;
alter table public.company_memberships add column if not exists member_email text;
alter table public.company_memberships add column if not exists company_role text default 'viewer';
alter table public.company_memberships add column if not exists status text default 'active';
alter table public.company_memberships add column if not exists invited_by_user_id uuid;
alter table public.company_memberships add column if not exists joined_at timestamptz;
alter table public.company_memberships add column if not exists created_at timestamptz default now();
alter table public.company_memberships add column if not exists updated_at timestamptz default now();

create unique index if not exists ux_company_memberships_company_email_v1432
  on public.company_memberships (company_id, lower(member_email));
create unique index if not exists ux_company_memberships_profile_v1432
  on public.company_memberships (user_id)
  where user_id is not null;
create index if not exists idx_company_memberships_company_v1432
  on public.company_memberships (company_id, status, company_role);

create table if not exists public.company_invitations (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  invitee_email text not null,
  company_role text not null check (company_role in ('manager', 'editor', 'viewer')),
  token_hash text not null,
  status text not null default 'pending' check (status in ('pending', 'accepted', 'revoked', 'expired')),
  invited_by_user_id uuid references public.users_profile(id) on delete set null,
  accepted_by_user_id uuid references public.users_profile(id) on delete set null,
  expires_at timestamptz not null,
  accepted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.company_invitations add column if not exists company_id uuid;
alter table public.company_invitations add column if not exists invitee_email text;
alter table public.company_invitations add column if not exists company_role text;
alter table public.company_invitations add column if not exists token_hash text;
alter table public.company_invitations add column if not exists status text default 'pending';
alter table public.company_invitations add column if not exists invited_by_user_id uuid;
alter table public.company_invitations add column if not exists accepted_by_user_id uuid;
alter table public.company_invitations add column if not exists expires_at timestamptz;
alter table public.company_invitations add column if not exists accepted_at timestamptz;
alter table public.company_invitations add column if not exists created_at timestamptz default now();
alter table public.company_invitations add column if not exists updated_at timestamptz default now();

create unique index if not exists ux_company_invitations_token_hash_v1432
  on public.company_invitations (token_hash);
create unique index if not exists ux_company_invitations_active_email_v1432
  on public.company_invitations (company_id, lower(invitee_email))
  where status = 'pending';
create index if not exists idx_company_invitations_company_status_v1432
  on public.company_invitations (company_id, status, expires_at);

-- Existing company owners are backfilled as active owners. The update is
-- idempotent and does not infer memberships for non-owner customer accounts.
insert into public.company_memberships (
  company_id,
  user_id,
  member_email,
  company_role,
  status,
  joined_at,
  created_at,
  updated_at
)
select
  c.id,
  p.id,
  lower(p.email),
  'owner',
  'active',
  coalesce(c.created_at, now()),
  coalesce(c.created_at, now()),
  now()
from public.companies c
join public.users_profile p on p.id = c.owner_user_id
where p.email is not null
on conflict (company_id, lower(member_email)) do nothing;

alter table public.company_memberships enable row level security;
alter table public.company_invitations enable row level security;

-- Direct Supabase client access is intentionally limited to the caller's own
-- membership/invitation. Roster management happens through the backend with
-- capability checks and service-role credentials.
drop policy if exists company_memberships_select_self_v1432 on public.company_memberships;
create policy company_memberships_select_self_v1432 on public.company_memberships
  for select
  using (
    user_id in (
      select id from public.users_profile where auth_user_id = auth.uid()
    )
  );

drop policy if exists company_invitations_select_invitee_v1432 on public.company_invitations;
create policy company_invitations_select_invitee_v1432 on public.company_invitations
  for select
  using (lower(invitee_email) = lower(coalesce(auth.jwt() ->> 'email', '')));
