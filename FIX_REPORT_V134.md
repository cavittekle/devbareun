# DevBareun v1.3.4 — Real Storage Upload + Project Ownership Enforcement

## Scope
This patch moves the SaaS upload flow from UI-only metadata recording toward real private storage behavior while preserving the existing DevBareun design.

## Added
- Supabase signed upload URL flow is now connected to the frontend upload page.
- Browser uploads files to the signed private storage URL with progress feedback.
- Backend marks files as `uploaded` only after the browser upload completes.
- Each uploaded file keeps `DB-FILE-*`, `project_id`, `owner_email`, `storage_bucket`, and `storage_path` metadata.
- File deletion validates ownership and marks the file deleted; Supabase object deletion is attempted when available.
- Project create/list/detail routes now support Supabase bearer-token ownership.
- Analysis creation validates file/project ownership and blocks analysis for files that are not uploaded or do not belong to the project.
- Frontend upload list keeps each file name, type, size, status, and progress visible.

## Version
`1.3.4-real-storage-upload-ownership`

## Production notes
- Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET` on backend only.
- The service-role key must never be exposed to frontend.
- Create a private Supabase Storage bucket named by `SUPABASE_STORAGE_BUCKET`.
- Configure Supabase CORS to allow the production frontend domain.
