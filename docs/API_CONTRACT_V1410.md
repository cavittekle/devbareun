# DevBareun API Contract v1.4.10

This release adds an explicit backend API contract gate so route cleanup does not regress during future refactors.

## Contract tool

Run from the repository root after backend dependencies are installed:

```bash
python tools/export_api_contract.py --root . --check --output /tmp/devbareun-api-contract.json
```

The tool imports `app.main`, enumerates FastAPI routes and checks:

- required canonical routes exist;
- retired legacy project routes are not exposed in OpenAPI;
- duplicate method/path registrations are not present;
- the React workspace does not reference retired endpoint snippets such as `/api/analysis/create` or `/api/workspace/guest-results`.

## Required canonical route families

The contract currently protects these route families:

```text
/api/auth/*
/api/projects/*
/api/uploads/*
/api/analysis/*
/api/dashboard/*
/api/reports/*
/api/billing/*
/api/credits/status
/api/subscriptions/status
/api/guest-result/{token}
/api/health
/api/readiness
/api/version
```

## Legacy project routes

The old token-based project flow remains mounted only as compatibility code and is disabled by default. These paths must stay out of OpenAPI unless explicitly exposed for a controlled migration:

```text
POST /api/projects
POST /api/projects/{project_id}/upload
POST /api/projects/{project_id}/preflight
POST /api/projects/{project_id}/analyze
GET  /api/projects/{project_id}/dashboard
GET  /api/projects/{project_id}/report/pdf
GET  /api/projects/{project_id}/report/excel
POST /api/payments/create-checkout
```

Default behavior remains `410 legacy_route_disabled`.

## Duplicate route cleanup

`/api/auth/me` and `/api/auth/logout` were previously registered twice through both `saas_public_routes.py` and `auth_routes.py`. The duplicated definitions were removed from `auth_routes.py`; `auth_routes.py` now owns pilot login and CSRF initialization, while the SaaS public router owns authenticated session profile/logout behavior.

## CI

The GitHub Actions workflow now runs the API contract check after backend dependencies are installed and before pytest. This catches accidental route changes before packaging.
