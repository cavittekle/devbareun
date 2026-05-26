# DevBareun Combined AgentOps Package v1.1.3

This package includes:

- `frontend/` — DevBareun frontend package
- `backend/` — DevBareun backend package
- `agents/devbareun_ops_engine/` — active DevBareun AgentOps system
- `tools/github_auto_upload.py` — safe GitHub sync tool for frontend/backend repositories

## Fixed release status

```text
Version: 1.1.3-fixed-release
Blocking Python/AgentOps crashes: fixed
SEO robots.txt issue: fixed
Parser template KPI priority: fixed
Runtime data/storage in ZIP: removed
GitHub clean-sync support: added
```

AgentOps may still show warnings locally when deployment secrets are not exported. Those are external configuration warnings, not package-code crashes.

## Recommended deployment

### Backend

Upload the contents of `backend/` to the `devbareun-backend` repository / Railway service.

Railway start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Minimum Railway environment variables:

```text
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,http://localhost:3000,http://localhost:5173
DEVBAREUN_MAX_FILES=12
DEVBAREUN_MAX_FILE_MB=30
DEVBAREUN_MAX_TOTAL_MB=120
DEVBAREUN_ENABLE_MOCK_PAYMENT=true
```

For commercial launch, configure Stripe and set:

```text
DEVBAREUN_ENABLE_MOCK_PAYMENT=false
STRIPE_SECRET_KEY=...
STRIPE_PRICE_ID=...
```

### Frontend

Upload the contents of `frontend/` to the `devbareun-frontend` repository / Vercel project.

### AgentOps local run example

From the package root that contains `frontend/`, `backend/`, and `agents/`:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports
```

Strict mode:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports --strict
```

Generated reports:

```text
agent_reports/agentops_supervisor_report.md
agent_reports/agentops_supervisor_report.json
agent_reports/construction_marketing_research.json
agent_reports/release_notes_v1_1_3_fixed_release.json
```

## GitHub auto-upload

Dry run:

```bash
python tools/github_auto_upload.py --root . --dry-run
```

Safe PR sync:

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python tools/github_auto_upload.py --root .
```

Clean sync, which also removes old files from target repos when they no longer exist locally:

```bash
python tools/github_auto_upload.py --root . --clean
```

Do not commit API keys, tokens, Railway secrets, Vercel secrets, Stripe secrets, OpenAI keys, or `.env` files to GitHub.
