# Backend Route Refactor v1.4.2

This refactor separates legacy project endpoints from the FastAPI application shell and splits the previous SaaS monolith into focused route modules.

## What changed

### 1. `main.py` is now the application shell

`backend/app/main.py` now owns only:

- FastAPI app creation
- CORS and security middleware
- exception handlers
- router registration
- health/version endpoints
- template manifest endpoints

Legacy project upload/analyze/report logic has been removed from the application shell.

### 2. Legacy project endpoints moved to `legacy_routes.py`

Legacy local-project endpoints now live in:

```text
backend/app/legacy_routes.py
```

The moved endpoints are:

```text
POST /api/projects
POST /api/projects/{project_id}/upload
POST /api/payments/create-checkout
POST /api/projects/{project_id}/preflight
POST /api/projects/{project_id}/analyze
GET  /api/projects/{project_id}/dashboard
GET  /api/projects/{project_id}/report/pdf
GET  /api/projects/{project_id}/report/excel
```

They still require:

```text
DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES=true
```

Otherwise they return a controlled `410 legacy_route_disabled` response.

The legacy router is excluded from OpenAPI by default. To expose it in API docs for transition testing:

```text
DEVBAREUN_EXPOSE_LEGACY_PROJECT_ROUTES=true
```

### 3. Template metadata moved to `template_manifest.py`

The shared template registry now lives in:

```text
backend/app/template_manifest.py
```

This avoids duplicating template metadata between the app shell and legacy preflight logic.

### 4. SaaS monolith split

The former `backend/app/saas_routes.py` has been reduced to a router aggregator.

New modules:

```text
backend/app/saas_common.py
backend/app/saas_public_routes.py
backend/app/saas_admin_routes.py
backend/app/saas_super_admin_routes.py
backend/app/saas_routes.py
```

Responsibilities:

| Module | Responsibility |
|---|---|
| `saas_common.py` | Shared request models, auth/session helpers, admin permission helpers, production store helpers |
| `saas_public_routes.py` | Public SaaS/auth/storage/project/file/analysis/payment/status endpoints |
| `saas_admin_routes.py` | `/api/admin/*` endpoints |
| `saas_super_admin_routes.py` | `/api/super-admin/*` compatibility aliases delegating to admin handlers |
| `saas_routes.py` | Aggregates the split routers for `main.py` |

Backward-compatible import support is kept for `_can_access` because the release/security tests import it from `app.saas_routes`.

## Canonical route direction

Production code should prefer these dedicated route families where possible:

```text
/api/auth/*
/api/uploads/*
/api/analysis/*
/api/dashboard/*
/api/billing/*
/api/reports/*
/api/workspace/*
```

The moved legacy local-project endpoints should be treated as transition-only compatibility routes.

## Validation performed

```text
python -m compileall -q backend/app agents/devbareun_ops_engine
cd backend && pytest -q
```

Result:

```text
6 passed
```
