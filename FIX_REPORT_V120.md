# DevBareun v1.2.0 — Five Control Packages + Light Mode + F-2 Terminology

## Requested changes implemented

1. **Light mode readability fix**
   - Upload wizard stepper now has dedicated light-mode colors.
   - Active/inactive step text, number circles, lines, cards, upload panels and action bars have light-theme-specific contrast rules.

2. **F-2 terminology standard**
   - Azerbaijani mode uses **F-2**.
   - English mode uses **Progress Payment** in visible UI/report strings.
   - Dynamic dashboard glossary maps EN backend terms back to F-2 in AZ mode.

3. **Five professional control packages**
   - Full Project Control
   - Schedule Recovery
   - Cost & Payment Control
   - Material Continuity
   - Risk & Decisions

4. **Backend and dashboard support**
   - Backend analysis type normalization now supports `material` and `risk`.
   - Parser priority supports material/procurement and risk/decision-oriented sheets.
   - Analyzer creates Material Continuity and Risk & Decisions dashboard sections.
   - Result dashboard renderer recognizes material and risk dashboards.

5. **Agent and release metadata updated**
   - Construction marketing/research agent now tracks all five control packages.
   - Release manifest updated to `1.2.0-control-packages-light-f2`.

## Changed files

- frontend/index.html
- frontend/css/styles.css
- frontend/js/i18n-extended.js
- frontend/js/backend-integration.js
- frontend/js/result-analysis-specific.js
- frontend/js/az-glossary.js
- frontend/js/app.js
- backend/app/analyzer.py
- backend/app/parser.py
- backend/app/main.py
- backend/app/version.py
- agents/devbareun_ops_engine/construction_marketing_research_agent.py
- AGENTOPS_RELEASE_MANIFEST.json

## Validation

- JavaScript syntax checks passed for all frontend JS files.
- Python compile checks passed for backend app and agents.
