# DevBareun v0.8.1 — Baseline vs Actual Analysis Logic

This release adds a strict baseline-vs-actual product rule for Cost and Schedule analysis.

## Core rule

No actual data → no actual result.
Unclear actual data → needs confirmation.
Confirmed actual data → calculate dashboard.

## Cost

A Cost Estimate / Smeta file creates a budget-only dashboard unless F-2, interim payment, invoice, or confirmed actual cost data is uploaded.

## Schedule

A baseline schedule creates a planning summary unless actual progress, actual finish, remaining duration, or forecast finish data is uploaded.

## Backend health

Expected version: `0.8.1-baseline-actual-logic`
