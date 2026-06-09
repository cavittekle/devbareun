# Supabase Deploy Order

For a clean DevBareun v1.4.0 production setup, run these files in the Supabase SQL Editor in this order:

1. `2026_05_29_v140_production_saas_core.sql`
2. `2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `2026_06_08_v141_super_admin_workspace.sql`
4. `seed_plans.sql`

Then create a private storage bucket:

```text
project-files
```

Required backend Railway env values:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=project-files
DEVBAREUN_ADMIN_EMAILS=owner@devbareun.com
```

Do not place `SUPABASE_SERVICE_ROLE_KEY` in Vercel/frontend env values.
