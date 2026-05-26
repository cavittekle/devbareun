# DevBareun v1.2.8 — Mapping Wizard QA Fix

Internal QA was run against v1.2.7 Template System + Data Mapping Wizard.

## Fixed

- Mapping Wizard no longer marks a required field as detected only because a column name was mapped.
- `detected_required_fields` now means the parser has a confirmed value.
- `mapped_required_fields` now separately lists fields that have a mapped column/source but no confirmed value yet.
- This prevents confusing UI states such as `actual_cost` appearing both detected and missing.

## Version

`1.2.8-mapping-wizard-qa-fix`
