# DevBareun Backend v1.1.3

FastAPI backend for DevBareun construction analytics, project-control parsing, dashboard generation and PDF/Excel exports.

## Current version

```text
1.1.3-fixed-release
```

## Main fixes in this package

- Unified backend health/version marker through `app/version.py`.
- Added server-side upload limits: file count, per-file MB and total MB.
- Replaced open CORS wildcard with environment-controlled allowed origins.
- Added project-id and filename validation guards.
- Added optional Stripe Checkout creation path while keeping pilot mock unlock configurable.
- Prioritized the official `Full_Dashboard_Input` template sheet so planned/actual KPI columns are read deterministically.
- Protected workforce fields from negative variance values being treated as worker counts.
- Removed runtime `data/` and `storage/` contents from the package.

## Railway start command

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Health check

```text
/health
/api/health
```

Expected version:

```text
1.1.3-fixed-release
```

## Environment variables

Copy `backend/.env.example` when configuring Railway.

Important variables:

```text
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,http://localhost:3000,http://localhost:5173
DEVBAREUN_MAX_FILES=12
DEVBAREUN_MAX_FILE_MB=30
DEVBAREUN_MAX_TOTAL_MB=120
DEVBAREUN_ENABLE_MOCK_PAYMENT=true
STRIPE_SECRET_KEY=
STRIPE_PRICE_ID=
```

For commercial launch, set Stripe credentials and disable pilot mock unlock:

```text
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
```

## Notes

- Calculations remain deterministic in Python.
- Optional OpenAI-assisted mapping is available through `OPENAI_MAPPING_ENABLED=true`; it should classify unclear data only, not replace Python calculations.
- Store runtime uploads and project JSON outside GitHub in production storage/database.
