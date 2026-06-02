# DevBareun Backend v0.8.1 — Baseline vs Actual Analysis Logic

This release adds strict baseline-vs-actual guardrails for Cost and Schedule analysis.

## Rule

No actual data → no actual result.
Unclear actual data → needs confirmation.
Confirmed actual data → calculate dashboard.

## Cost

Cost Estimate / Smeta files create a budget-only dashboard unless confirmed F-2, interim payment, invoice, or actual cost data is present.

## Schedule

Baseline schedule files create a planning summary unless actual progress, actual finish, remaining duration, or forecast finish data is present.

## Version

Expected health version: `0.8.1-baseline-actual-logic`
