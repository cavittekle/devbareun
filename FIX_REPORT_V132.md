# DevBareun v1.3.2 — Supabase Auth + Storage Integration

## Scope

This release converts the existing DevBareun SaaS skeleton toward real production ownership by adding Supabase Auth and private storage integration points without changing the current public website design.

## Added

- Supabase Auth register/login bridge.
- Supabase access token validation endpoint.
- Local DevBareun user synchronization from Supabase user payloads.
- Private Supabase Storage signed upload URL endpoint.
- Private Supabase Storage signed download URL endpoint.
- File ownership metadata with `project_id`, `file_id`, `owner_email`, `storage_bucket`, and `storage_path`.
- Frontend SaaS helper client for session, login, register and signed uploads.
- Supabase Auth + Storage setup guide.
- Backend `.env.example` entries for Supabase.

## New backend endpoints

```text
POST /api/auth/supabase/register
POST /api/auth/supabase/login
GET  /api/auth/me
POST /api/storage/create-upload-url
POST /api/storage/create-download-url
```

## Required backend env

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=replace_with_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=replace_with_service_role_key_backend_only
SUPABASE_STORAGE_BUCKET=devbareun-project-files
```

## Security notes

- `SUPABASE_SERVICE_ROLE_KEY` belongs only in backend deployment variables.
- Storage bucket should remain private.
- Downloads should use signed URLs.
- User-facing file access must pass Supabase token validation and project/file ownership checks.

## QA performed

```text
python compile backend/app/supabase_client.py: PASS
python compile backend/app/saas_routes.py: PASS
node --check frontend/js/supabase-saas-client.js: PASS
```

## Next recommended release

`v1.3.3 — Protected Dashboard + Project History`

The next stage should wire the existing dashboard pages to the authenticated user session, project list, analysis history and saved report records.
