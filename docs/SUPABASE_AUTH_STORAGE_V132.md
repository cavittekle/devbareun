# DevBareun v1.3.2 — Supabase Auth + Storage Integration

This stage keeps the existing DevBareun frontend and backend design, but adds the real SaaS ownership layer required for production.

## What is added

- Supabase Auth registration/login bridge.
- Token validation endpoint for protected dashboard access.
- Local SaaS user synchronization from Supabase Auth user payloads.
- Supabase Storage signed upload URL endpoint.
- Supabase Storage signed download URL endpoint.
- File ownership metadata linked to `project_id`, `file_id`, and `owner_email`.
- Secure storage bucket path format.

## Required environment variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-backend-only
SUPABASE_STORAGE_BUCKET=devbareun-project-files
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` in the frontend.

## Backend endpoints added

```text
POST /api/auth/supabase/register
POST /api/auth/supabase/login
GET  /api/auth/me
POST /api/storage/create-upload-url
POST /api/storage/create-download-url
```

## Auth flow

1. User registers through `/api/auth/supabase/register`.
2. Supabase creates the auth user.
3. Backend creates or updates the DevBareun local SaaS user record.
4. User logs in through `/api/auth/supabase/login` or frontend Supabase client.
5. Frontend stores the Supabase access token in the user session.
6. Protected API requests send:

```http
Authorization: Bearer <supabase_access_token>
```

## Storage flow

1. User creates/selects a project.
2. Frontend calls `/api/storage/create-upload-url` with project ID and file metadata.
3. Backend validates the Supabase token and project ownership.
4. Backend creates a `DB-FILE-000001` style file ID.
5. Backend returns a signed Supabase upload URL.
6. Frontend uploads the file directly to Supabase Storage.
7. Backend stores metadata in `uploaded_files`.

## Storage path format

```text
projects/{project_id}/{file_id}/{original_filename}
```

Example:

```text
projects/DB-PRJ-000001/DB-FILE-000001/D3_progress.xlsx
```

## Supabase bucket

Create a private bucket:

```text
devbareun-project-files
```

The bucket must not be public. Downloads should use signed URLs.

## Production checklist

- Enable email confirmation if required.
- Configure redirect URLs in Supabase Auth.
- Add Row Level Security policies to database tables.
- Keep service role key only in Railway/Render backend env.
- Store uploaded files in private Supabase Storage bucket.
- Use signed URLs for uploads/downloads.
- Audit all admin endpoints before public launch.
