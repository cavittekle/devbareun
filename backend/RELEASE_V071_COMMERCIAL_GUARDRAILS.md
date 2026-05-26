# DevBareun Backend v0.7.1 — Commercial Accuracy Guardrails

## Purpose
Protect commercial dashboards from presenting suspicious extracted values as confirmed KPI results.

## Changes
- If detected actual completed cost is greater than the detected smeta/contract total, it is held as `Needs confirmation`.
- `actual_execution` is only calculated from a validated actual completed amount.
- PDF/Excel/dashboard risk and action messages now explain when F-2 totals, VAT, duplicate cumulative totals, or approved variations require confirmation.
- Confidence score is reduced when commercial confirmation is required.
- Cost and Progress dashboard primary KPI cards show `Needs confirmation` instead of a misleading over-baseline amount.

## Health check
Expected backend version:

```text
0.7.1-commercial-accuracy-guardrails
```
