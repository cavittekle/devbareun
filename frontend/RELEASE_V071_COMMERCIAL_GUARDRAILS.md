# DevBareun v0.7.1 — Commercial Accuracy Guardrails

This full package keeps the latest frontend and adds backend commercial guardrails.

Expected backend health version:

```text
0.7.1-commercial-accuracy-guardrails
```

Main behavior: suspicious actual completed cost values that exceed the smeta/contract total are no longer shown as confirmed KPI values. They are marked as `Needs confirmation` until the user confirms the F-2 total, VAT treatment, duplicate cumulative total, or approved variation.
