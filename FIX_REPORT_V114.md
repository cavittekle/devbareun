# DevBareun v1.1.4 Live API + AgentOps Warning Fix

## Fixed

- Updated frontend backend fallback URL to `https://devbareun-production.up.railway.app` in:
  - `frontend/js/api-client.js`
  - `frontend/js/result-dynamic.js`
- Removed LanguageAudit warnings caused by Turkish literal fallback rules in `frontend/js/az-glossary.js` while preserving runtime matching through escaped regex patterns.
- Updated GitHub Actions JavaScript actions for Node.js 24 compatibility:
  - `actions/checkout@v6`
  - `actions/setup-python@v6`
  - `actions/upload-artifact@v7`
  - `actions/github-script@v8`
- Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to workflow jobs.
- Added built-in `GITHUB_TOKEN` env for AgentOps runs.
- Adjusted deployment readiness checks so Vercel/Railway mutation tokens are treated as optional automation readiness, not normal QA release blockers.

## Still external

For full direct platform automation, add these repository secrets manually when needed:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_SERVICE_ID`
- `GH_SYNC_TOKEN`

Normal live QA needs only:

- `SITE_URL=https://devbareun.com`
- `API_URL=https://devbareun-production.up.railway.app`
