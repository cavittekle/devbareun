# Supabase Setup Guide

## 1. Create Project

1. Create a Supabase project.
2. Save the project URL and anon key.
3. Save the service role key only for the backend deployment.

## 2. Database

Run the SQL files in this order from the Supabase SQL editor:

1. `database/supabase_schema.sql`
2. `database/seed_plans.sql`
3. `database/2026_05_27_v136_persistent_analysis.sql`
4. `database/2026_05_27_v137_report_archive_print.sql`
5. `database/2026_05_27_v138_admin_panel.sql`
6. `database/2026_05_27_v138_billing_gate_usage.sql`
7. `database/2026_05_27_v139_production_security.sql`
8. `database/rls_policies.sql`

Review RLS policies before launch and test with a real Supabase Auth user.

## 3. Storage

Create a private bucket:

```text
devbareun-project-files
```

Keep public access off. Uploaded project files must be served through backend authorization, not direct public bucket URLs.

## 4. Backend Variables

Set in Railway:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=replace_with_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=replace_with_service_role_key_backend_only
SUPABASE_STORAGE_BUCKET=devbareun-project-files
```

## 5. Frontend Variables

Set in Vercel only if a build step or public Supabase client is introduced:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=replace_with_supabase_anon_key
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` in frontend code or Vercel public variables.
