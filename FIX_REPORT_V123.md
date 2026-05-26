# DevBareun v1.2.3 — Statistical Analytics Layer

## Purpose
This release adds a deterministic statistical analytics layer to DevBareun so construction project dashboards behave more like a data analytics product, not only a KPI display.

## Added
- Backend statistical analytics engine: `backend/app/statistics_engine.py`
- Descriptive statistics: count, min, max, mean, median, range, variance, standard deviation, coefficient of variation
- Variance analysis: cost, progress and workforce baseline-vs-actual gaps
- Trend analysis: linear regression, slope, R², trend direction and next-period forecast
- Moving average: 3-point sequence smoothing
- Correlation analysis: Pearson correlation where paired data exists
- Outlier detection: z-score based abnormal value checks
- Forecasting: indicative final cost and overrun projection
- Frontend dashboard section: Statistical analytics, variance, forecast, correlation, outlier checks and available analytics functions
- AZ glossary additions for statistical/data analytics terms

## Safety model
The statistical layer does not invent missing data. It only calculates from parsed KPI values, F-2/progress payment evidence, workforce/productivity evidence, risk components and detected sheet profiles.

## Changed files
- `backend/app/statistics_engine.py`
- `backend/app/analyzer.py`
- `backend/app/version.py`
- `frontend/js/result-analysis-specific.js`
- `frontend/js/az-glossary.js`
- `frontend/css/result-analysis-specific.css`
- `AGENTOPS_RELEASE_MANIFEST.json`
