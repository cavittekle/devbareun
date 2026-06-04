# DevBareun Ops Engine v1.1.0

This package adds a full agent system for DevBareun.

## Included agents

1. `BackendSyntaxAgent`
2. `BackendParserAccuracyAgent`
3. `FrontendReadabilityAgent`
4. `LanguageAuditAgent`
5. `SeoAuditAgent`
6. `SecuritySecretsAgent`
7. `DeploymentReadinessAgent`
8. `SiteManagerAgent`
9. `BrowserQaAgent`
10. `ConstructionMarketingResearchAgent`
11. `ReleaseManagerAgent`
12. `ChiefSupervisorAgent` — controls all agents and writes the final management report.

## Run locally

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports
```

Strict mode:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --out agent_reports --strict
```

## Environment variables for live management

```bash
SITE_URL=https://devbareun.com
API_URL=https://devbareun-backend-production.up.railway.app
GITHUB_TOKEN=...
VERCEL_TOKEN=...
VERCEL_ORG_ID=...
VERCEL_PROJECT_ID=...
RAILWAY_TOKEN=...
RAILWAY_PROJECT_ID=...
RAILWAY_SERVICE_ID=...
```

The agents do not directly overwrite production. They report, test, and prepare controlled CI/CD decisions.
Production release, payment logic, database migration, secret changes and DNS changes should remain manual-approval actions.
