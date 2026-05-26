# DevBareun v1.2.2 — Advanced Analysis Engine

## Release decision
Pilot/demo ready with stronger analysis transparency. This patch moves DevBareun from a static dashboard toward construction decision-support.

## Main additions

### 1. Data readiness and confidence explanation
Every generated dashboard now includes an advanced `data_readiness` section:
- confidence score and level;
- positive evidence detected from uploaded files;
- weak or missing evidence;
- package-specific data gap notes.

### 2. Missing data panel
The backend now builds missing-data guidance by selected control package:
- Full Project Control;
- Schedule Recovery;
- Cost & Payment Control;
- Material Continuity;
- Risk & Decisions.

The system flags missing baseline, actual, workforce, material, progress payment and risk/decision data without inventing values.

### 3. Audit trail
A source evidence trail was added using detected sheet profiles:
- source sheet/file label;
- detected type;
- confidence;
- mapped columns/evidence.

This improves trust in how the dashboard reached its result.

### 4. How-calculated transparency
The dashboard now includes formula notes for available metrics:
- Remaining Value = Cost Estimate / Smeta - Confirmed Progress Payment;
- Cost Variance % = (Actual Confirmed Cost - Smeta Baseline) / Smeta Baseline × 100;
- Progress Gap = Planned Progress - Actual Progress;
- Delay Impact = Forecast Finish - Baseline Finish;
- Workforce Gap = Current Workforce - Required Workforce;
- Risk Score = weighted component model.

### 5. What-if scenarios
Scenario prompts are generated based on available data:
- current pace vs recovery crew;
- remaining commercial buffer;
- current cost trend continues;
- material delivery delay;
- data completion scenario when evidence is insufficient.

### 6. Action tracker
Recommended actions are converted into management tracking rows:
- action;
- owner;
- deadline;
- status;
- priority.

This makes the dashboard more PMO-oriented and less like a static report.

## Frontend additions
`frontend/js/result-analysis-specific.js` now renders advanced panels:
- Data readiness;
- Missing data;
- How calculated;
- What-if scenarios;
- Audit trail;
- Action tracker.

`frontend/css/result-analysis-specific.css` includes dark/light responsive styles for the new advanced sections.

## Backend additions
`backend/app/analyzer.py` now produces:
- `dashboard_sections.advanced_sections.data_readiness`
- `dashboard_sections.advanced_sections.missing_data`
- `dashboard_sections.advanced_sections.audit_trail`
- `dashboard_sections.advanced_sections.how_calculated`
- `dashboard_sections.advanced_sections.what_if`
- `dashboard_sections.advanced_sections.action_tracker`

`dashboard.data_quality` also includes readiness, missing data and audit trail outputs.

## Version
`1.2.2-advanced-analysis-engine`

## Files changed
- backend/app/analyzer.py
- backend/app/version.py
- frontend/js/result-analysis-specific.js
- frontend/js/az-glossary.js
- frontend/css/result-analysis-specific.css
- agents/devbareun_ops_engine/construction_marketing_research_agent.py
- AGENTOPS_RELEASE_MANIFEST.json
