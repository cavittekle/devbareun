# Deployment Roots

DevBareun has two production deploy targets. The repository root is not a deploy target.

## Vercel

- Root Directory: `frontend`
- Config file: `frontend/vercel.json`
- Entry page: `frontend/index.html`
- Do not deploy the repository root.
- Do not copy backend-only secrets into Vercel.

## Railway

- Root Directory: `backend`
- Config file: `backend/railway.json`
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Keep Supabase service role keys and payment secrets only in Railway.

## Supabase

- SQL files stay in `database/`.
- Apply migrations before enabling live auth, storage, or billing.

## OpenAI Sites

- Adapter directory: `sites/devbareun`
- The adapter packages the existing static files from `frontend/`; it does not maintain a second website implementation.
- Sites deployments are an additional hosted surface and do not replace the approved Vercel `frontend` or Railway `backend` production roots.
- Private backend values and payment secrets remain outside the Sites bundle.

## Why this matters

There is no production `index.html` in the repository root. This prevents an
accidental Vercel root deployment from serving an old landing page.
