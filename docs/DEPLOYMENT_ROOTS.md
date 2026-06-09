# Deployment Roots

DevBareun has two deploy targets. The repository root is not a deploy target.

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

## Why this matters

There is no production `index.html` in the repository root. This prevents an
accidental Vercel root deployment from serving an old landing page.
