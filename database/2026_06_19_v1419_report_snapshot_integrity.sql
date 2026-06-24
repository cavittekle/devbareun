-- DevBareun v1.4.19: report snapshot integrity and download audit.
--
-- Reports are generated from a frozen dashboard payload. This migration stores
-- snapshot metadata and exposes a service-role-only atomic download counter.
-- It is additive and safe after the v1.4.18 schema.

begin;

alter table public.reports add column if not exists payload_sha256 text;
alter table public.reports add column if not exists content_sha256 text;
alter table public.reports add column if not exists snapshot_version text default 'v1';
alter table public.reports add column if not exists generated_at timestamptz default now();
alter table public.reports add column if not exists last_downloaded_at timestamptz;
alter table public.reports add column if not exists download_count integer not null default 0;

update public.reports
set generated_at = coalesce(generated_at, created_at, now()),
    snapshot_version = coalesce(snapshot_version, case when report_payload is not null and report_payload <> '{}'::jsonb then 'v1' else null end),
    download_count = coalesce(download_count, 0)
where generated_at is null
   or snapshot_version is null
   or download_count is null;

create index if not exists idx_reports_project_generated_v1419
  on public.reports(project_id, generated_at desc);

create index if not exists idx_reports_owner_generated_v1419
  on public.reports(lower(owner_email), generated_at desc);

alter table public.reports drop constraint if exists reports_payload_sha256_format_v1419;
alter table public.reports add constraint reports_payload_sha256_format_v1419
  check (payload_sha256 is null or payload_sha256 ~ '^[a-f0-9]{64}$') not valid;
alter table public.reports validate constraint reports_payload_sha256_format_v1419;

alter table public.reports drop constraint if exists reports_content_sha256_format_v1419;
alter table public.reports add constraint reports_content_sha256_format_v1419
  check (content_sha256 is null or content_sha256 ~ '^[a-f0-9]{64}$') not valid;
alter table public.reports validate constraint reports_content_sha256_format_v1419;

-- Caller authorization remains in the FastAPI report route. The function is
-- deliberately executable only by service_role so browser clients cannot inflate
-- the audit counter directly.
create or replace function public.record_report_download(p_report_id uuid)
returns table (report_id uuid, download_count integer, last_downloaded_at timestamptz)
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.reports
     set download_count = coalesce(public.reports.download_count, 0) + 1,
         last_downloaded_at = now(),
         updated_at = now()
   where public.reports.id = p_report_id
     and coalesce(public.reports.status, 'ready') <> 'deleted'
  returning public.reports.id, public.reports.download_count, public.reports.last_downloaded_at;
end;
$$;

revoke all on function public.record_report_download(uuid) from public;
revoke all on function public.record_report_download(uuid) from anon;
revoke all on function public.record_report_download(uuid) from authenticated;
grant execute on function public.record_report_download(uuid) to service_role;

commit;
