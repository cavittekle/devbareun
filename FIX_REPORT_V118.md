# DevBareun v1.1.8 — Three Control Package Release

## Purpose
This release simplifies the public analysis model from five technical choices into three professional construction-control packages:

1. **Schedule Recovery** — Schedule / Delay + Workforce
2. **Cost & Payment Control** — Cost Estimate + Progress Payment / F-2
3. **Full Dashboard** — combined premium view of all modules

## Frontend changes
- Rebuilt the upload/analysis selector into three large package cards.
- Preserved the approved dark futuristic wizard visual language.
- Default selected package: **Full Dashboard**.
- Added selected package summary strip.
- Updated EN/AZ copy and required-data logic for the new packages.
- Kept all functional IDs/buttons intact:
  - `analysisTypeGrid`
  - `dropZone`
  - `fileInput`
  - `fileList`
  - `generatePreviewBtn`
  - `clearFilesBtn`
  - `mappingPreviewPanel`
  - `templateDownload`

## Backend changes
- `schedule` analysis now works as **Schedule Recovery** and extracts workforce productivity evidence as part of the same flow.
- `cost` analysis is now branded as **Cost & Payment Control** and keeps cost/F-2/payment dashboard logic.
- `all` analysis is now branded as **Full Dashboard**.
- Backend version updated to `1.1.8-control-packages`.

## Result dashboard changes
- Analysis-specific dashboard labels updated:
  - `Schedule Recovery Dashboard`
  - `Cost & Payment Control Dashboard`
  - `Full Project Control Dashboard`
- Schedule dashboard now surfaces workforce and recovery-resource KPIs.
- Cost dashboard now focuses on smeta, F-2/payment evidence and commercial risk.

## AgentOps changes
- Marketing research agent updated around the new 3-package positioning.
- Frontend readability agent updated to validate the new package-card workflow markers.
- Language audit agent updated to check new package translation keys.

## QA result
Local AgentOps run:
- BackendSyntaxAgent: PASS
- BackendParserAccuracyAgent: PASS
- FrontendReadabilityAgent: PASS
- LanguageAuditAgent: PASS
- SeoAuditAgent: PASS
- SecuritySecretsAgent: PASS
- GitHubSyncAgent: PASS
- SiteManagerAgent: PASS
- BrowserQaAgent: PASS
- ConstructionMarketingResearchAgent: PASS
- ReleaseManagerAgent: PASS

Only deployment warnings remain when `SITE_URL` / `API_URL` are not configured in local run environment. These are expected outside GitHub Actions secrets.
