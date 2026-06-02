# DevBareun v1.2.6 — Statistical Guardrails Fix

## Purpose
This patch fixes statistical edge cases identified during review of the construction analytics layer.

## Fixes

### 1. EAC early-stage guardrail
EAC is no longer calculated when actual progress is below 5%. This prevents unrealistic values such as actual cost × 200 when actual progress is 0.5%.

New fields:
- `eac_method`
- `eac_confidence`
- `eac_warning`

### 2. Forecast guardrail
Final cost forecast is no longer calculated from actual/progress extrapolation when actual progress is below 10%.

Trend-based forecast also requires at least 4 valid detected periods.

### 3. Linear regression minimum sample size
Regression now requires at least 4 data points. With fewer points it returns:
- `direction: Insufficient data`
- `forecast_next: null`
- reliability note explaining the minimum requirement.

### 4. Correlation minimum sample size
Pearson correlation now requires at least 4 paired points. This prevents misleading `r = 1.000` results from two-point comparisons.

### 5. Material low-stock logic
Low stock detection no longer flags every item below median. It now uses:

```text
low stock if stock < 20% of detected mean stock
```

This is still a fallback until richer consumption-rate and lead-time inputs are available.

### 6. Action tracker owner assignment
Action owners are now assigned semantically by action text:
- Cost / payment / smeta / F-2 → Commercial/QS
- Material / supplier / delivery → Procurement
- Workforce / site / crew → Site Team
- Risk / approval / decision → Management
- Schedule / recovery / forecast → Project Control

The previous order-based fallback has been removed.

### 7. F-2 period bridge
The statistics layer now reads F-2 period data from:
- `evidence.f2_periods`
- `evidence.az_f2_parser.periods`
- fallback `evidence.f2_completed_amount` only if period data is unavailable.

## Validation
Manual checks confirm:
- 0.5% progress no longer produces huge EAC.
- 2-point regression/correlation returns insufficient data.
- 4 F-2 periods produce a valid trend.
- Median-based low-stock false positives are removed.

## Version
`1.2.6-statistical-guardrails`
