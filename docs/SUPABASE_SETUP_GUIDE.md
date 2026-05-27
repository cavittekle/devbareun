
# Supabase Setup Guide

1. Create Supabase project.
2. Open SQL editor.
3. Run `database/supabase_schema.sql`.
4. Run `database/seed_plans.sql`.
5. Review and run `database/rls_policies.sql` after connecting Supabase Auth user IDs.
6. Create private storage bucket:
   - `project-files`
   - public access: off
7. Add backend env variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_STORAGE_BUCKET`
8. Add frontend env variables if a Next/Supabase frontend shell is introduced:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Do not expose the service role key in frontend code.
