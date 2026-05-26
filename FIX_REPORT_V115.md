# DevBareun v1.1.5 — Result Dashboard Language and Dropdown Fix

Date: 2026-05-26

## Fixed

- Fixed dark-mode report-language dropdown readability on the result dashboard.
- Forced readable option colors for dark and light themes.
- Added Azerbaijani translations for remaining result-dashboard labels and placeholder rows.
- Added automatic Azerbaijani DOM post-translation for dynamic backend-rendered result text.
- Replaced result-page Azerbaijani wording that still used English-style “dashboard” with “panel” wording where appropriate.
- Removed remaining Turkish audit keyword from `az-glossary.js` while preserving runtime translation rules.

## Changed files

- `frontend/css/result-dashboard.css`
- `frontend/js/az-glossary.js`
- `frontend/js/result-dashboard.js`
- `frontend/js/result-dynamic.js`

## QA

Local AgentOps check:

- BackendSyntaxAgent: PASS
- BackendParserAccuracyAgent: PASS
- FrontendReadabilityAgent: PASS
- LanguageAuditAgent: PASS
- SeoAuditAgent: PASS
- SecuritySecretsAgent: PASS

No Turkish hardcoded text warning remains in local LanguageAuditAgent.
