-- v1.5.0: project uploads carry a document type for the delay analysis.
--   contract  - construction contract (PDF, Word, photo/scan)
--   schedule  - programme (Excel/CSV, Primavera XER, MS Project XML/MPP, PDF)
--   f2        - F2 certificates of completed work (Excel/CSV, Word)
-- Existing rows stay NULL; the backend then infers the type from the file name.

alter table public.uploaded_files
  add column if not exists document_type text;

alter table public.uploaded_files
  drop constraint if exists uploaded_files_document_type_check_v150;

alter table public.uploaded_files
  add constraint uploaded_files_document_type_check_v150
  check (document_type is null or document_type in ('contract', 'schedule', 'f2'));

create index if not exists idx_uploaded_files_project_document_type
  on public.uploaded_files(project_id, document_type);
