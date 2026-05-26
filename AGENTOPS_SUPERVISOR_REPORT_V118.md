# DevBareun AgentOps Supervisor Report

Generated: `2026-05-26T16:19:24.613276+00:00`

## Decision: `REVIEW_BEFORE_RELEASE`

- Average score: **97.3**
- Passed: **11**
- Warnings: **1**
- Failed: **0**

## Agent Results

| Agent | Status | Score | Summary |
|---|---:|---:|---|
| BackendSyntaxAgent | pass | 100 | No issues detected. |
| BackendParserAccuracyAgent | pass | 98 | info: 1 |
| FrontendReadabilityAgent | pass | 100 | No issues detected. |
| LanguageAuditAgent | pass | 100 | No issues detected. |
| SeoAuditAgent | pass | 100 | No issues detected. |
| SecuritySecretsAgent | pass | 100 | No issues detected. |
| DeploymentReadinessAgent | warn | 76 | warning: 2 |
| GitHubSyncAgent | pass | 98 | info: 1 |
| SiteManagerAgent | pass | 98 | info: 1 |
| BrowserQaAgent | pass | 98 | info: 1 |
| ConstructionMarketingResearchAgent | pass | 100 | No issues detected. |
| ReleaseManagerAgent | pass | 100 | No issues detected. |

## Findings

### BackendParserAccuracyAgent
- **info** `backend/app`: Backend parser coverage check completed without blocking issues..

### DeploymentReadinessAgent
- **warning**: Live QA URL not set: SITE_URL. Recommendation: Set SITE_URL and API_URL as GitHub Actions secrets for live site/API checks.
- **warning**: Live QA URL not set: API_URL. Recommendation: Set SITE_URL and API_URL as GitHub Actions secrets for live site/API checks.

### GitHubSyncAgent
- **info**: GITHUB_TOKEN/GH_TOKEN is not set. Auto-upload dry-run works; live sync needs GH_SYNC_TOKEN or a GitHub token.. Recommendation: Add GH_SYNC_TOKEN only if you want the auto-upload workflow to push/PR changes.

### SiteManagerAgent
- **info**: Live site checks skipped because SITE_URL/API_URL are not configured.. Recommendation: Set SITE_URL and API_URL in GitHub Actions secrets to enable uptime checks.

### BrowserQaAgent
- **info**: SITE_URL not set; browser QA skipped.. Recommendation: Set SITE_URL=https://devbareun.com or a Vercel preview URL.
