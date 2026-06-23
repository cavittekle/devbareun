# DevBareun v1.4.13 Database Contract Gate

This release adds a static Supabase contract check so schema drift is caught before deployment.

## What changed

- Added `tools/check_database_contract.py`.
- Added `database/2026_06_19_v1413_database_contract_bridge.sql`.
- Added backend tests for table/column/RLS/storage coverage.
- Added the database contract check to CI and the release gate.

## Contract coverage

The checker parses the SQL files listed in `database/SUPABASE_DEPLOY_ORDER.md` and verifies:

- required production tables exist;
- backend-required columns exist;
- RLS is enabled on customer, project, analysis, billing and admin tables;
- each protected table has at least one policy;
- the private `project-files` storage bucket and storage object policies are present;
- the v1.4.13 bridge migration is included in deploy order.

## Run locally

```bash
python tools/check_database_contract.py --root .
python tools/check_database_contract.py --root . --json
```

## Deploy order

Run this migration after the durable worker migration and before seed/admin setup:

```text
2026_06_18_v145_analysis_worker.sql
2026_06_19_v1413_database_contract_bridge.sql
seed_plans.sql
promote_owner_info_devbareun.sql
production_rls_audit.sql
```

The bridge migration is additive and idempotent. It adds compatibility aliases and timestamp columns used by the cleaned backend/admin/read-model code.
