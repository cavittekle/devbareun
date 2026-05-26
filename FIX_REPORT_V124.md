# DevBareun v1.2.4 — Construction Statistical Analytics Fix

## Purpose
The previous v1.2.3 layer added general data analytics functions. This patch refocuses the statistical layer on construction project control needs.

## What changed
- Generic analytics panel now becomes **Construction Statistical Analytics**.
- Added construction-specific controls:
  - Earned Value Management: PV, EV, AC, CV, SV, CPI, SPI.
  - Forecasting: EAC, ETC, VAC and final cost projection.
  - Cost & Payment: smeta vs Progress Payment/F-2 variance, payment utilization, commercial buffer and overbilling watch.
  - Schedule Recovery: plan/fact progress gap, delay, recovery pressure and additional workers required.
  - Workforce: current vs required workforce variance.
  - Material Continuity: material stock statistics and low-stock candidates.
  - Risk & Decisions: weighted risk score and decision level.
  - Outlier checks for work package/payment/quantity anomalies.
  - Construction correlation checks between progress, cost, workforce and material indicators.

## Updated files
- backend/app/statistics_engine.py
- backend/app/version.py
- frontend/js/result-analysis-specific.js
- frontend/js/az-glossary.js
- frontend/css/result-analysis-specific.css
- AGENTOPS_RELEASE_MANIFEST.json

## Version
`1.2.4-construction-statistical-analytics`
