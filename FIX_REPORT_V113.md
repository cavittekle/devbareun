# DevBareun v1.1.3 Fixed Release Report

## Package

```text
devbareun_agentops_v113_fixed_release.zip
```

## Fixed

- Fixed `GitHubSyncAgent` import/base-class crash.
- Fixed `BackendParserAccuracyAgent` `self.issues` crash.
- Added `.gitignore` rules for runtime data, uploads, reports, cache and secrets.
- Removed `backend/data/` and `backend/storage/` from the deliverable package.
- Fixed `frontend/robots.txt` formatting.
- Unified backend/release version marker to `1.1.3-fixed-release` through `backend/app/version.py`.
- Added backend upload limits via environment variables.
- Replaced open CORS wildcard with environment-controlled origin allow-list.
- Added project-id and upload filename validation guards.
- Added optional Stripe Checkout creation path, while keeping pilot mock unlock configurable.
- Prioritized official `Full_Dashboard_Input` sheet in parser.
- Prevented negative variance values from being interpreted as workforce counts.
- Added GitHub auto-upload `--clean` mode to remove stale files from target repos.
- Added GitHub Actions input for clean sync.
- Removed nested duplicate AgentOps/workflow folders from `frontend/` and `backend/` deploy folders.
- Updated deployment and backend connection documentation.

## Local validation

Backend smoke test passed:

```text
GET /health -> 1.1.3-fixed-release
POST /api/projects -> 200
POST /api/projects/{id}/upload -> 200
POST /api/projects/{id}/preflight -> 200
POST /api/payments/create-checkout -> 200 mock_pilot
POST /api/projects/{id}/analyze -> 200
GET /api/projects/{id}/report/pdf -> 200
GET /api/projects/{id}/report/excel -> 200
```

Professional template parser validation:

```text
total_cost: 3,139,625.02
planned_cost: 3,139,625.02
actual_cost: 1,874,000.00
cost_variance_percent: -40.31
planned_execution: 70.00
actual_execution: 59.70
delay_days: 8
workforce_current: 19
workforce_required: 25
```

AgentOps validation:

```text
10 agents passed.
2 agents warned only because local deployment secrets/tokens were not exported.
0 agents failed.
```

Remaining external configuration needed before live automation:

```text
GITHUB_TOKEN / GH_SYNC_TOKEN
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
RAILWAY_TOKEN
RAILWAY_PROJECT_ID
RAILWAY_SERVICE_ID
SITE_URL
API_URL
```
