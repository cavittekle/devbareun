# DevBareun v1.0.7 — Full Dynamic Language Audit

This release fixes the remaining dynamic EN/TR -> AZ language inconsistencies across the upload mapping flow and generated result dashboards.

## Fixed
- Upload mapping KPI labels, detected sheet types and missing-field messages now localize through a shared AZ glossary.
- Turkish dynamic phrases such as `Maliyet`, `Gerçekte`, `Planlanan yürütme`, `Başlangıç bitiş`, `Tahmini bitiş`, `İsteğe bağlı` are normalized to Azerbaijani when AZ mode is active.
- Result dashboard dynamic cards, labels, status chips, risk register rows, recommended actions and empty-state messages now pass through the same localization layer.
- `Manual` wording in AZ UI replaced with clearer Azerbaijani wording (`Əllə`).

## Health version
`1.0.7-full-dynamic-language-audit`
