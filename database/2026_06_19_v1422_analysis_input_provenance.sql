-- DevBareun v1.4.22 — Analysis input provenance snapshots
-- Apply after v1.4.21. Additive and idempotent.
--
-- Analysis jobs and results retain a privacy-safe manifest of the uploaded
-- file metadata, checksum verification and deterministic security-screening
-- status that contributed to an analysis. Storage paths, signed URLs and
-- provider secrets are intentionally not stored in this snapshot.

alter table public.analysis_jobs add column if not exists input_manifest jsonb default '{}'::jsonb;
alter table public.analysis_jobs add column if not exists input_manifest_sha256 text;
alter table public.analysis_jobs add column if not exists input_file_count integer default 0;
alter table public.analysis_jobs add column if not exists provenance_schema_version text default 'v1';

alter table public.analysis_results add column if not exists input_manifest jsonb default '{}'::jsonb;
alter table public.analysis_results add column if not exists input_manifest_sha256 text;
alter table public.analysis_results add column if not exists input_file_count integer default 0;
alter table public.analysis_results add column if not exists provenance_schema_version text default 'v1';

update public.analysis_jobs
set input_manifest = coalesce(input_manifest, '{}'::jsonb),
    input_file_count = greatest(coalesce(input_file_count, 0), 0),
    provenance_schema_version = coalesce(nullif(provenance_schema_version, ''), 'v1')
where input_manifest is null
   or input_file_count is null
   or input_file_count < 0
   or provenance_schema_version is null
   or provenance_schema_version = '';

update public.analysis_results
set input_manifest = coalesce(input_manifest, '{}'::jsonb),
    input_file_count = greatest(coalesce(input_file_count, 0), 0),
    provenance_schema_version = coalesce(nullif(provenance_schema_version, ''), 'v1')
where input_manifest is null
   or input_file_count is null
   or input_file_count < 0
   or provenance_schema_version is null
   or provenance_schema_version = '';

alter table public.analysis_jobs drop constraint if exists analysis_jobs_input_file_count_v1422;
alter table public.analysis_jobs add constraint analysis_jobs_input_file_count_v1422
  check (input_file_count is null or input_file_count >= 0);

alter table public.analysis_results drop constraint if exists analysis_results_input_file_count_v1422;
alter table public.analysis_results add constraint analysis_results_input_file_count_v1422
  check (input_file_count is null or input_file_count >= 0);

create index if not exists idx_analysis_results_provenance_fingerprint_v1422
  on public.analysis_results(project_id, input_manifest_sha256, created_at desc);
