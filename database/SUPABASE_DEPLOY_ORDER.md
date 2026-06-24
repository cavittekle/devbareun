# Supabase Deploy Order

For a clean DevBareun v1.4.34 production setup, run these files in the Supabase SQL Editor in this order:

1. `2026_05_29_v140_production_saas_core.sql`
2. `2026_05_29_v140_part2_jobs_billing_reports.sql`
3. `2026_06_08_v141_super_admin_workspace.sql`
4. `2026_06_18_v142_canonical_api_bridge.sql`
5. `2026_06_18_v145_analysis_worker.sql`
6. `2026_06_19_v1413_database_contract_bridge.sql`
7. `2026_06_19_v1416_analysis_worker_observability.sql`
8. `2026_06_19_v1417_analysis_job_recovery.sql`
9. `2026_06_19_v1418_analysis_idempotency.sql`
10. `2026_06_19_v1419_report_snapshot_integrity.sql`
11. `2026_06_19_v1420_upload_checksum_integrity.sql`
12. `2026_06_19_v1421_upload_security_screening.sql`
13. `2026_06_19_v1422_analysis_input_provenance.sql`
14. `2026_06_20_v1423_panel_access_boundaries.sql`
15. `2026_06_20_v1424_audit_integrity.sql`
16. `2026_06_20_v1425_audit_archive_outbox.sql`
17. `2026_06_21_v1430_data_lifecycle_requests.sql`
18. `2026_06_21_v1431_billing_lifecycle_integrity.sql`
19. `2026_06_21_v1432_company_team_foundation.sql`
20. `2026_06_21_v1433_project_sharing.sql`
21. `2026_06_21_v1434_project_activity_timeline.sql`
22. `seed_plans.sql`
23. `promote_owner_info_devbareun.sql` after `info@devbareun.com` exists in Supabase Auth
24. `production_rls_audit.sql` as a read-only verification query

Then create a private storage bucket:

```text
project-files
reports
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


For durable analysis execution on Railway, set the web service to queue-only mode and run a second worker service from the same backend root:

```text
DEVBAREUN_ANALYSIS_JOB_MODE=worker
python -m app.analysis_worker --loop --interval 10 --batch-size 1
```


## Worker observability

After the v1.4.16 migration, use the staff-protected endpoint below to verify that a Railway worker is live without exposing user payloads or provider secrets:

```text
GET /api/analysis/operations
```

A running analysis job refreshes `analysis_jobs.last_heartbeat_at` while parser work is in progress. The separate `analysis_worker_heartbeats` table records the worker's last poll/result signal.


## Failed-job recovery

After v1.4.17, stale jobs that exhaust `max_attempts` enter `dead_lettered` rather than returning to the queue indefinitely. Staff can inspect `GET /api/analysis/operations/recovery-jobs` and explicitly requeue a reviewed job via `POST /api/analysis/operations/jobs/{job_id}/retry`. A dead-lettered job requires `{"reset_attempts": true}`. Do not retry a job when a completed result already exists.


## Report snapshot integrity

After v1.4.19, each newly generated report stores the analysis payload used for its output, together with SHA-256 metadata. Existing reports remain downloadable through a compatibility fallback, but new reports should show `snapshot_available: true`. The staff/backend-only `record_report_download` RPC increments archive telemetry atomically.


## Upload checksum integrity

After v1.4.20 each modern browser upload sends a SHA-256 checksum. The analysis worker recomputes that checksum after downloading the private object and rejects a mismatched source file before parser execution or credit consumption. Set `DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM=true` for production; legacy files without a checksum remain visible as `not_provided` until re-uploaded.

For final read-only verification, run `production_rls_audit.sql` last.


## Upload security screening and quarantine gate

After v1.4.21, every file is screened by the worker after its checksum is verified and before parser execution. `security_scan_status=clean` with `quarantine_status=released` means the deterministic admission checks passed. `blocked` or `failed` files are quarantined and excluded from later analysis starts.

This is not a malware/antivirus service. It checks format signatures, unsafe OOXML archive structures, bounded archive expansion, macro presence and selected active-PDF markers. Set `DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS=true` or `DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT=true` only when the deployment policy requires hard blocking of those findings.


## Analysis input provenance

After v1.4.22, each analysis job and completed result retains a privacy-safe source manifest and a deterministic `source_fingerprint`. Apply `2026_06_19_v1422_analysis_input_provenance.sql` after v1.4.21 before deploying the web and worker services. The manifest must not contain storage paths or signed URLs.


## Panel access boundaries

After v1.4.23, apply `2026_06_20_v1423_panel_access_boundaries.sql` after v1.4.22. It normalizes legacy `admin`/`user` labels and enforces the canonical `customer`, `owner`, `support`, `analyst`, `finance`, `operator` role set. Worker queue operations are limited to `owner` and `operator`; do not use customer status actions to modify staff accounts.


## Audit integrity

After v1.4.24, new internal audit events are written through the `append_audit_event` RPC. The audit table is append-only: direct update/delete operations are rejected by a database trigger. Apply `2026_06_20_v1424_audit_integrity.sql` after v1.4.23, then verify the owner-only `GET /api/super-admin/audit-integrity` endpoint after web deployment. Legacy audit rows remain readable but are not retroactively included in the v1 hash chain.


## External audit archive outbox

After v1.4.25, every integrity-version `1` audit event creates an immutable, privacy-safe snapshot in `audit_archive_outbox` within the same transaction. Deploy a separate Railway service using `backend/railway.audit-archive.json`:

```text
python -m app.audit_archive_worker --loop --interval 15 --batch-size 25
```

Set `DEVBAREUN_AUDIT_ARCHIVE_MODE=webhook` plus a HTTPS `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL` and `DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET` on all Railway services. The worker signs deliveries with `X-DevBareun-Audit-Signature`. Review owner-only `GET /api/super-admin/audit-archive` for pending/retry/dead-letter state. A dead-lettered item is never auto-reset; retry it only after review with `POST /api/super-admin/audit-archive/{archive_id}/retry` and `{"reset_attempts": true}`.


## Backup and recovery

v1.4.26 through v1.4.29 do not introduce an additional Supabase SQL migration.
Before production sign-off, apply the backup policy to Railway services and
complete an isolated restore preflight using `tools/backup_recovery.py`. Keep
any direct `DEVBAREUN_BACKUP_DATABASE_URL` only in the secure backup operator
environment, never in Vercel or Railway application services.


## Data lifecycle and retention

After v1.4.30, apply `2026_06_21_v1430_data_lifecycle_requests.sql` after
v1.4.25. It creates privacy export/erasure request records and soft-delete
retention metadata. It does not automatically purge storage, audit records,
payments, reports, backups or Supabase Auth identities. Configure the same
retention policy values across Railway web/analysis/archive worker services:

```text
DEVBAREUN_SOFT_DELETE_RETENTION_DAYS=30
DEVBAREUN_ERASURE_GRACE_DAYS=14
DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS=7
DEVBAREUN_AUTO_PURGE_ENABLED=false
```


## Billing webhook lifecycle integrity

After v1.4.31, apply `2026_06_21_v1431_billing_lifecycle_integrity.sql` after
v1.4.30. It adds a bounded, retry-safe payment webhook event state machine and
persists the DevBareun checkout ID in Lemon Squeezy custom metadata. Set the
same value on every Railway service:

```text
DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS=5
```

Use `GET /api/billing/checkouts/{checkout_id}` only through an authenticated
customer or staff session. The endpoint does not disclose payment URLs, raw
provider payloads or customer data.


## Project activity timeline

After v1.4.34, project collaborators can use `GET /api/project-activity/{project_id}`. Apply `2026_06_21_v1434_project_activity_timeline.sql` after v1.4.33 and deploy the web service plus analysis worker together; analysis completion events are emitted by the worker. The timeline is append-only and project-scoped. It is not a replacement for the global audit hash chain.
