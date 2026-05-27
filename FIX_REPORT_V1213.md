# DevBareun v1.2.13 — Adaptive Package-Specific Dashboards

## Purpose
Make every analysis package use its own dashboard logic while keeping dashboards flexible for different customer data structures.

## Fixed
- Empty KPI cards are filtered before rendering.
- Empty panel rows are filtered before rendering.
- Package dashboards no longer force modules without uploaded evidence.
- Adaptive dashboard profile exposes active and suppressed blocks.
- Frontend result dashboard renderer was rebuilt to avoid blank trend/statistics/what-if/action sections.

## Package behavior
- Full Project Control: consolidated view, only available blocks are shown.
- Schedule Recovery: schedule/workforce recovery evidence is prioritized.
- Cost & Payment Control: smeta/progress payment/commercial metrics are prioritized.
- Material Continuity: procurement/material evidence is prioritized.
- Risk & Decisions: risk, decision and management-action evidence is prioritized.

## Validation
- Python compile: PASS
- Frontend JS syntax: PASS
