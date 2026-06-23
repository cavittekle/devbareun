# Changelog

## v1.4.34 — Project Activity Timeline

- Added a project-scoped, append-only activity timeline for uploads, analyses, reports and access changes.
- Added explicit project-role authorization for timeline reads.
- Added privacy-safe event metadata redaction and a v1.4.34 Supabase migration.

v1.4.33 — Explicit Project Sharing

- Added explicit project-scoped grants for active company members: viewer, editor and manager.
- Kept owner access implicit and project deletion owner-only.
- Added grant tenancy validation, project-access API, Workspace management screen, authorization audit events and contract checks.

## v1.4.32 — Company Team Foundation

- Added company workspace bootstrap, active member roster and controlled manual invitation records.
- Invitation tokens are shown once, stored only as SHA-256 hashes and accepted only by the exact invited email address.
- Added owner/manager governance for invitations and non-owner membership role/status updates.
- Deliberately retained current project/file/report ownership rules; company membership does not grant cross-user project access yet.
- Added v1.4.32 migration, workspace UI, audit-event integration, contract checks and operator guidance.


## v1.4.31 — Billing lifecycle integrity

- Persisted an internal checkout lifecycle record before returning each Lemon Squeezy checkout URL.
- Added an authenticated checkout-status endpoint and bounded workspace polling after provider return.
- Added retry-safe payment webhook claiming/completion RPCs so an event is not marked processed before entitlement side effects finish.
- Added provider-period-aware subscription updates; monthly usage resets only when the provider billing period advances.
- Added idempotent one-time credit grants tied to a provider event and refund handling that revokes only unused credits.
- Added v1.4.31 migration, provider parity/env validation, static contract checks and operator guidance.


## v1.4.28 — Privacy-Safe Error Telemetry

- Added structured request and worker telemetry with request ID correlation.
- Added optional Sentry delivery for sanitized synthetic errors only.
- Added telemetry readiness, operations health coverage, provider parity checks and release contracts.

# Changelog


## v1.4.30 — Data lifecycle and privacy request workflow

- Added customer export/erasure request endpoints with explicit erasure confirmation.
- Added owner-only review queue and privacy capability boundary.
- Added soft-delete retention metadata (`purge_after_at`, `retention_status`).
- Added v1.4.30 migration and data lifecycle contract checker.
- Physical destructive purge remains deliberately out of scope for this release.


## v1.4.29 - Backup and disaster-recovery controls

- Added `tools/backup_recovery.py` for guarded database dump, private Storage inventory and restore-preflight validation. The tool has no production restore command.
- Added `docs/BACKUP_AND_RECOVERY_V1429.md` with proposed RPO/RTO, operator scope, isolated restore drill and incident escalation procedures.
- Added `deploy/env/backup-operator.env.template`; direct backup database credentials are now explicitly separated from Railway/Vercel runtime configuration.
- Added backup policy validation and Railway service parity checks.
- Added CI/release-gate backup recovery contract coverage.
- Updated backend version/env label to `1.4.29`.


## v1.4.27 — Guarded Production Pilot Acceptance

- Added a dependency-free authenticated acceptance tool for read-only verification and explicitly confirmed project/upload/analysis/report pilot paths.
- Defaulted the tool to non-destructive mode; project creation, analysis-credit consumption and frozen report generation each require separate confirmation flags.
- Added redacted evidence output, credential handling through process environment variables only, deployment-runbook integration and CI safety contract checks.


## v1.4.26 — Operational Health

- Added a staff-safe cross-service health summary for runtime readiness, analysis worker state and external audit archive delivery.
- Added owner/operator API access and a Super Admin Operations health panel tab with incident-code-only output.
- Added operational health contract checks, regression tests and incident runbook guidance.


## v1.4.25 — Audit Archive Outbox

- Added transactional external audit archive outbox, HMAC-signed webhook delivery worker, bounded retry/dead-letter handling and owner-only reviewed retry.
- Added archive queue/worker status to Super Admin audit area and Railway archive-worker deployment configuration.

## v1.4.24 — Audit integrity and append-only trail

- Added request-correlated audit context with bounded `X-Request-ID` propagation.
- Added metadata redaction, deterministic metadata hashes and a database-side append-only audit hash chain for new events.
- Added an immutable audit trigger, RPC-based audit writing, owner-only integrity status endpoint and Super Admin integrity view.
- Added v1.4.24 migration, release contract checker, regression tests and operator guidance.

## v1.4.23 — Panel Access Boundaries

- Added a single canonical role/permission policy shared by customer-workspace, Super Admin, upload, report and analysis routes.
- Replaced broad staff bypasses with resource capabilities so support/finance cannot read cross-tenant project, upload, analysis or report data.
- Restricted worker operations and manual recovery to owner/operator.
- Blocked customer-status operations against staff accounts; staff changes remain owner-only.
- Added v1.4.23 migration, static contract checks, regression tests and role-boundary documentation.

## v1.4.22 — Analysis Input Provenance

- Added privacy-safe, deterministic input manifests for analysis jobs and completed results.
- Persisted source fingerprint, file count, parser-integrity/screening states and engine version without storage paths or signed URLs.
- Exposed the snapshot through executive dashboards, frozen report payloads and the workspace result traceability panel.
- Added v1.4.22 migration, static contract checker, regression tests and deployment guidance.

## v1.4.21 — Upload Security Screening and Quarantine Gate

- Added deterministic parser-admission screening for materialized uploads: signature re-check, safe OOXML archive bounds, macro detection and selected active-PDF findings.
- Added quarantine metadata so blocked or failed files cannot re-enter analysis jobs.
- Added the v1.4.21 Supabase migration, worker/web configuration parity checks, regression tests and operator guidance.
- This layer is explicitly not an antivirus/malware-scanning service.

## v1.4.20 — Upload Checksum Integrity

- Added SHA-256 source-file verification from browser upload through worker parser download.
- Added upload checksum migration, contract checks, frontend hashing and mismatch-safe analysis failure behavior.

v1.4.19 — Report Snapshot Integrity and Download Audit

- Frozen report payloads at generation time so later analyses cannot silently change an archived export.
- Added SHA-256 snapshot/content metadata and private no-store download headers.
- Added atomic, service-role-only report download audit RPC and report lifecycle contract checks.


## v1.4.18 — Analysis Idempotency and Atomic Usage Ledger

- Added Idempotency-Key support and active-job deduplication for analysis starts.
- Added a Supabase atomic usage ledger RPC to prevent duplicate subscription/credit consumption.
- Added result/billing reconciliation for jobs that crash after result persistence.
- Added database, API, frontend and release-gate contract checks for the new integrity model.

## v1.4.17 — Analysis job recovery and dead-letter guard

- Added a bounded `DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS` policy for newly-created worker jobs.
- Added explicit `dead_lettered` handling for stale jobs that exhaust their retry budget.
- Added staff-safe failed/dead-letter inspection and explicit single-job recovery endpoints.
- Blocked recovery of jobs that already have a persisted result to avoid duplicate output generation.
- Added the v1.4.17 additive Supabase recovery migration, deployment guidance, config parity checks, and regression tests.

## v1.4.16 — Analysis worker observability

- Added periodic heartbeats for long-running parser and analytics jobs.
- Added the `analysis_worker_heartbeats` migration/table and protected staff operations endpoint.
- Added degraded/stopped worker lifecycle signals, safe queue aggregation, and deployment documentation.

## v1.4.15 - Production configuration preflight

- Added provider-specific safe templates for Railway web, Railway worker and Vercel under `deploy/env/`.
- Added `tools/check_provider_config.py` to check Railway web/worker parity, worker mode, public URL/Supabase alignment and Vercel backend-secret exclusion without printing values.
- Added `docs/PRODUCTION_CONFIG_PREFLIGHT_V1415.md` and linked the preflight into the deployment runbook and environment matrix.
- Updated CI and release-gate requirements to protect the templates and configuration preflight tool.
- Narrowed package hygiene filters so the tracked `deploy/env/` template directory is retained while actual virtual environments remain excluded.
- Updated backend version/env label to `1.4.15`.


## v1.4.14 - Production deployment runbook gate

- Added `docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md` with the ordered Supabase, Railway web, Railway worker, Vercel, Lemon Squeezy, smoke-test and rollback procedure.
- Added `docs/DEPLOYMENT_ENV_MATRIX_V1414.md` to separate Railway/backend-only secrets from Vercel/public frontend values.
- Added `tools/check_deploy_runbook.py` to machine-check runbook coverage, deploy-order references, provider files and CI integration.
- Added backend tests for the deployment runbook contract and env matrix private-secret scope.
- Updated CI and release gate to run the deployment runbook checker.
- Updated backend version/env label to `1.4.14`.
- Expected backend test result: `31 passed`.


## v1.4.13 - Database contract gate

- Added `tools/check_database_contract.py` to statically verify deploy-order Supabase tables, required backend columns, RLS coverage, table policies and storage bucket policy surface.
- Added `database/2026_06_19_v1413_database_contract_bridge.sql` for additive compatibility columns discovered by the schema contract.
- Added backend regression tests for the database contract.
- Updated CI and release gate to run the database contract check.
- Updated backend version/env label to `1.4.13`.
- Expected backend test result: `27 passed`.


## v1.4.11 - Frontend asset restoration

- Restored the public `frontend/assets/` brand bundle used by favicon, logo, Open Graph, manifest and workspace references.
- Added `tools/check_frontend_assets.py` to scan frontend asset references and fail when a required logo/favicon/static asset is missing.
- Updated release gate required-file checks so clean packages must include the core brand assets.
- Updated CI to run the frontend asset checker before env validation/build/test.
- Added `docs/FRONTEND_ASSETS_V1411.md` with the asset policy.
- Updated backend version/env label to `1.4.11`.


## v1.4.12 - Package Completeness Audit

- Added static frontend deploy-surface validation for `frontend/workspace/`.
- Included the built React workspace in the clean source package.
- Added template manifest validation to release/CI checks.
- Documented the clean-package comparison against the original v1.4.0 archive.

## v1.4.10 - API contract and route deduplication

- Added `tools/export_api_contract.py` to export/check FastAPI route manifests without scraping a deployed server.
- Added backend API contract tests that assert canonical routes exist, retired project routes stay out of OpenAPI, and React workspace code does not call deprecated endpoints.
- Removed duplicate `/api/auth/me` and `/api/auth/logout` registrations from `auth_routes.py`; canonical implementations remain in the SaaS public router.
- Updated CI and release gate checks to include the API contract tool.
- Added `docs/API_CONTRACT_V1410.md` with the route-contract policy.
- Updated backend version/env label to `1.4.10`.
- Expected backend test result: `23 passed`.


## v1.4.9 - Release gate and package hygiene

- Added dependency-free `tools/release_gate.py` for required-file, package hygiene, secret-pattern, env-file, version, migration deploy-order, frontend package and CI checks.
- Added dependency-free `tools/package_release.py` for clean zip creation with SHA-256 manifest output.
- Updated CI to run the release gate and env-example validation before frontend/backend build and test steps.
- Added `docs/RELEASE_GATE_V149.md` with the pre-release command sequence.
- Updated backend version/env label to `1.4.9`.
- Expected backend test result: `18 passed`.


## v1.4.8 - Production readiness gates

- Added `/api/readiness` with secret-safe release-blocking errors and warnings.
- Added cross-platform `tools/validate_production_env.py` for backend/frontend env validation.
- Added cross-platform `tools/smoke_deploy.py` for deployed frontend/backend smoke testing.
- Extended runtime readiness with CSRF requirement and analysis worker mode visibility.
- Updated backend env example to `DEVBAREUN_ANALYSIS_JOB_MODE=worker` and v1.4.8 readiness label.
- Added `docs/PRODUCTION_READINESS_V148.md`.
- Expected backend test result: `16 passed`.


## v1.4.7 - Result Dashboard UX

- Replaced the result viewer raw-JSON-first screen with executive KPI cards, schedule/progress bars, data-quality indicators, risk register rows and recommended actions.
- Added payload normalization for executive dashboard, saved analysis result and guest result response shapes.
- Kept technical JSON behind an explicit audit/debug toggle instead of rendering it as the primary result view.

## v1.4.5 - 2026-06-18


## v1.4.6 - Parser regression guardrails

- Added parser/analyzer regression tests for smeta-only, smeta + F-2, baseline schedule without actual progress, and workforce-only analysis.
- Fixed actual-source detection so `az_f2_parser` metadata from smeta-only workbooks is not treated as confirmed progress-payment evidence unless it includes `completed_total` or `actual_execution`.
- Added fixture policy documentation for anonymized parser test data.
- Expected backend test result: `14 passed`.


### Added
- Durable table-backed analysis worker mode through `DEVBAREUN_ANALYSIS_JOB_MODE=worker`.
- `python -m app.analysis_worker` CLI for one-shot or looping job execution.
- `database/2026_06_18_v145_analysis_worker.sql` for worker lock, heartbeat, retry and payload columns.
- `backend/railway.worker.json` as a Railway worker-service reference config.
- `docs/ANALYSIS_WORKER_V145.md` with deployment and operational notes.

### Changed
- `/api/analysis/start/{project_id}` now returns `execution_mode` so frontend/operators can distinguish background vs worker execution.
- Analysis job updates now write `updated_at` and heartbeat metadata when available.

### Reliability
- Stale `running` jobs can be returned to `queued` by the worker, or failed after maximum attempts.
- Worker execution uses the same parser, analytics, risk, persistence and credit-consumption pipeline as the previous BackgroundTasks path.

### Notes
- Production durable mode requires running the v1.4.5 migration before enabling `DEVBAREUN_ANALYSIS_JOB_MODE=worker`.

# Changelog

## v1.4.21 — Upload Security Screening and Quarantine Gate

- Added deterministic parser-admission screening for materialized uploads: signature re-check, safe OOXML archive bounds, macro detection and selected active-PDF findings.
- Added quarantine metadata so blocked or failed files cannot re-enter analysis jobs.
- Added the v1.4.21 Supabase migration, worker/web configuration parity checks, regression tests and operator guidance.
- This layer is explicitly not an antivirus/malware-scanning service.

All notable DevBareun changes should be documented here.

Use this file to prevent repeated work and to help Codex understand what was already changed.

## Format

```md
## vX.Y.Z - YYYY-MM-DD

### Added
- 

### Changed
- 

### Fixed
- 

### Removed
- 

### Security
- 

### Notes
- 
```

## Unreleased

### Added

- Codex project instruction structure.
- `AGENTS.md` for repository rules.
- `docs/PROJECT_STATE.md` for current project state.
- `docs/DEPLOYMENT_GUIDE.md` for deployment process.
- `docs/API.md` for backend API documentation.
- `docs/DATABASE.md` for database structure.
- `docs/AUTOMATIONS.md` for Codex automation prompts.
- `.env.example` for environment variable names.
- `.github/workflows/ci.yml` for basic CI.

### Changed

- 

### Fixed

- 

### Removed

- 

### Security

- Added rule to prevent committing real `.env` files and secrets.

### Notes

- Update this file after every accepted project package or production deployment.


## v1.4.4 - 2026-06-18

### Added
- `GET /api/auth/csrf` to initialize a frontend-readable CSRF cookie.
- `docs/SECURITY_HARDENING_V144.md` documenting the cookie-auth CSRF/Origin hardening.

### Changed
- React workspace and static API helpers now send `X-CSRF-Token` automatically for unsafe HTTP methods.
- Production static frontend no longer allows a localStorage override for persisted bearer tokens.

### Fixed
- Logout now clears both `devbareun_auth` and `devbareun_csrf` cookies.

### Security
- Cookie-authenticated mutating requests now require trusted `Origin`/`Referer` validation in production security mode.
- Double-submit CSRF token validation is available through `DEVBAREUN_REQUIRE_CSRF_TOKEN` and defaults on in production.

### Notes
- Deploy frontend and backend together when enabling `DEVBAREUN_REQUIRE_CSRF_TOKEN=true`.

## v1.4.2 - 2026-06-18

### Added
- `database/2026_06_18_v142_canonical_api_bridge.sql` for additive production schema/API compatibility.
- `docs/CANONICAL_API_SCHEMA_V142.md` documenting canonical API routes and deployment order.

### Changed
- Workspace project list/detail reads now use production Supabase rows when configured.
- React workspace starts analysis through `/api/analysis/start/{project_id}` instead of the legacy queue stub.
- Static `devbareun-api.js` upload/analyze helpers now prefer canonical upload and analysis endpoints.
- Credit consumption now updates both legacy and canonical credit counters.

### Fixed
- Production project creation/listing mismatch where projects were inserted into Supabase but listed from the local store.
- Billing checkout frontend handling now accepts `checkout_url` returned by the backend service.

### Notes
- Legacy project endpoints remain isolated in `backend/app/legacy_routes.py` and disabled by default.

## v0.1.0 - YYYY-MM-DD

### Added

- Initial documentation kit.
- Initial repository control files.
- Basic CI template.

### Changed

- 

### Fixed

- 

### Removed

- 

### Security

- 

### Notes

- Replace this placeholder version with the actual first accepted project version.
