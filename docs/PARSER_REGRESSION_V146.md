# DevBareun v1.4.6 Parser Regression Guardrails

v1.4.6 adds regression coverage around the highest-risk parser/analyzer rule: **do not create commercial or schedule KPIs without actual evidence**.

## What changed

### 1. Smeta-only actual-source detection fixed

The Azerbaijani F-2/Nokopitelni parser can record metadata such as `az_f2_parser.smeta_total` even when no F-2 completed amount exists. Before this release, that metadata could be treated as progress-payment evidence by the analyzer guardrail.

The analyzer now treats `az_f2_parser` as actual evidence only when it contains a confirmed `completed_total` or `actual_execution` value.

### 2. Regression test corpus added

New test module:

```text
backend/tests/test_parser_regression.py
```

The tests generate small synthetic workbooks/CSV files at runtime and validate the real parser + dashboard pipeline.

Covered cases:

```text
smeta_only.xlsx
  Baseline total is detected.
  actual_cost, actual_execution and cost_variance_percent stay empty.
  dashboard risk register asks for actual cost/payment data.

smeta_f2.xlsx
  Smeta total is detected.
  F-2 completed amount is detected.
  actual_cost and actual_execution are calculated from validated payment evidence.

baseline_schedule.csv
  Planned schedule/progress is detected.
  delay_days and schedule_gap are withheld because actual progress is missing.

workforce-only ParsedProjectData
  Workforce KPIs stay visible.
  commercial/schedule fields are cleared from the workforce dashboard.
```

## Why this matters

Construction project-control dashboards are only useful if they distinguish:

```text
baseline estimate / smeta
actual progress payment / F-2
actual schedule update
workforce recovery evidence
```

A smeta-only upload can support a baseline summary, but it must not produce fake actual execution, fake actual cost, fake cost variance or fake delay. v1.4.6 locks this rule with repeatable tests.

## Validation command

```bash
python -m compileall -q backend/app agents/devbareun_ops_engine
cd backend
pytest -q
```

Expected result for this release:

```text
14 passed
```
