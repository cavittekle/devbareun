# DevBareun AgentOps v1.1.0 Setup

This package adds a full agent system, including a Chief Supervisor agent that controls all other agents and produces reports.

## Main command

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports
```

## What the supervisor produces

- `agent_reports/agentops_supervisor_report.md`
- `agent_reports/agentops_supervisor_report.json`
- `agent_reports/construction_marketing_research.json`
- `agent_reports/release_notes_v1_1_0_agentops.json`

## GitHub/Vercel/Railway integration

The workflows are added under:

```text
.github/workflows/devbareun-agentops.yml
.github/workflows/devbareun-weekly-site-management.yml
```

For separated repositories, the same workflow is also copied under:

```text
frontend/.github/workflows/
backend/.github/workflows/
```

## Required secrets for full live automation

```text
GITHUB_TOKEN
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
RAILWAY_TOKEN
RAILWAY_PROJECT_ID
RAILWAY_SERVICE_ID
SITE_URL
API_URL
```

## Safety model

Agents can test, audit, report and prepare deployment decisions. They should not directly change:

- production payment logic
- Stripe prices or payment gate
- database destructive operations
- secrets and tokens
- DNS/domain settings
- production deploy without human approval
