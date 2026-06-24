-- DevBareun v1.4.0 Part 2
-- Background jobs, dashboard integration, billing usage and report archive columns.

alter table public.analysis_jobs add column if not exists owner_email text;
alter table public.analysis_jobs add column if not exists analysis_type text default 'all';
alter table public.analysis_jobs add column if not exists updated_at timestamptz default now();

alter table public.analysis_results add column if not exists status text default 'completed';
alter table public.analysis_results add column if not exists analysis_type text default 'all';

alter table public.reports add column if not exists report_name text;
alter table public.reports add column if not exists format text default 'PDF';
alter table public.reports add column if not exists media_type text;
alter table public.reports add column if not exists report_payload jsonb default '{}'::jsonb;

alter table public.payments add column if not exists project_id uuid;
alter table public.payments add column if not exists payment_provider text default 'lemonsqueezy';

create index if not exists idx_analysis_jobs_owner_email on public.analysis_jobs(owner_email);
create index if not exists idx_analysis_results_owner_email on public.analysis_results(owner_email);
create index if not exists idx_reports_owner_email on public.reports(owner_email);
create index if not exists idx_payments_owner_email on public.payments(owner_email);

drop policy if exists analysis_jobs_owner_or_admin_v140_part2 on public.analysis_jobs;
create policy analysis_jobs_owner_or_admin_v140_part2 on public.analysis_jobs
for all using (
  owner_email = auth.jwt() ->> 'email'
  or user_id = auth.uid()
  or exists (select 1 from public.users_profile p where p.auth_user_id = auth.uid() and p.role in ('admin', 'owner', 'support', 'analyst', 'finance', 'operator'))
)
with check (
  owner_email = auth.jwt() ->> 'email'
  or user_id = auth.uid()
  or exists (select 1 from public.users_profile p where p.auth_user_id = auth.uid() and p.role in ('admin', 'owner', 'support', 'analyst', 'finance', 'operator'))
);

drop policy if exists payments_owner_or_admin_v140_part2 on public.payments;
create policy payments_owner_or_admin_v140_part2 on public.payments
for select using (
  owner_email = auth.jwt() ->> 'email'
  or user_id = auth.uid()
  or exists (select 1 from public.users_profile p where p.auth_user_id = auth.uid() and p.role in ('admin', 'owner', 'support', 'analyst', 'finance', 'operator'))
);
