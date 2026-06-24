-- DevBareun v1.4.21 — Upload security screening and quarantine gate
-- Apply after v1.4.20. Additive and idempotent.
--
-- This migration records deterministic parser-admission screening metadata.
-- It does not claim to implement malware/antivirus scanning.

alter table public.uploaded_files add column if not exists security_scan_status text default 'pending';
alter table public.uploaded_files add column if not exists security_scan_engine text;
alter table public.uploaded_files add column if not exists security_scan_started_at timestamptz;
alter table public.uploaded_files add column if not exists security_scan_completed_at timestamptz;
alter table public.uploaded_files add column if not exists security_scan_error text;
alter table public.uploaded_files add column if not exists security_scan_findings jsonb default '[]'::jsonb;
alter table public.uploaded_files add column if not exists quarantine_status text default 'pending_scan';
alter table public.uploaded_files add column if not exists quarantine_reason text;
alter table public.uploaded_files add column if not exists quarantined_at timestamptz;

update public.uploaded_files
set security_scan_status = coalesce(nullif(security_scan_status, ''), 'pending'),
    security_scan_findings = coalesce(security_scan_findings, '[]'::jsonb),
    quarantine_status = coalesce(nullif(quarantine_status, ''), 'pending_scan')
where security_scan_status is null
   or security_scan_status = ''
   or security_scan_findings is null
   or quarantine_status is null
   or quarantine_status = '';

alter table public.uploaded_files drop constraint if exists uploaded_files_security_scan_status_v1421;
alter table public.uploaded_files add constraint uploaded_files_security_scan_status_v1421
  check (security_scan_status is null or security_scan_status in ('pending', 'scanning', 'clean', 'blocked', 'failed', 'skipped'));

alter table public.uploaded_files drop constraint if exists uploaded_files_quarantine_status_v1421;
alter table public.uploaded_files add constraint uploaded_files_quarantine_status_v1421
  check (quarantine_status is null or quarantine_status in ('pending_scan', 'released', 'quarantined'));

create index if not exists idx_uploaded_files_security_scan_v1421
  on public.uploaded_files(project_id, security_scan_status, quarantine_status, updated_at desc);
