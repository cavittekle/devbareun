-- DevBareun v1.4.20 — Upload checksum integrity
-- Apply after v1.4.19. Additive and idempotent.

alter table public.uploaded_files add column if not exists checksum_algorithm text;
alter table public.uploaded_files add column if not exists checksum_status text default 'not_provided';
alter table public.uploaded_files add column if not exists verified_checksum text;
alter table public.uploaded_files add column if not exists checksum_verified_at timestamptz;
alter table public.uploaded_files add column if not exists checksum_error text;

update public.uploaded_files
set checksum_algorithm = coalesce(nullif(checksum_algorithm, ''), case when checksum is not null and length(trim(checksum)) = 64 then 'sha256' else null end),
    checksum_status = coalesce(nullif(checksum_status, ''), case when checksum is not null and length(trim(checksum)) = 64 then 'pending_verification' else 'not_provided' end)
where checksum_algorithm is null or checksum_status is null or checksum_status = '';

create index if not exists idx_uploaded_files_checksum_status_v1420
  on public.uploaded_files(checksum_status, updated_at desc);

alter table public.uploaded_files drop constraint if exists uploaded_files_checksum_algorithm_v1420;
alter table public.uploaded_files add constraint uploaded_files_checksum_algorithm_v1420
  check (checksum_algorithm is null or checksum_algorithm in ('sha256'));

alter table public.uploaded_files drop constraint if exists uploaded_files_checksum_status_v1420;
alter table public.uploaded_files add constraint uploaded_files_checksum_status_v1420
  check (checksum_status is null or checksum_status in ('not_provided', 'pending_verification', 'verified', 'mismatch', 'invalid'));
