# DevBareun v0.8.4 — Upload Limits + Actual Data Request

## Changes

- The upload flow keeps one main **Choose Files** button.
- The file input supports multiple files in one selection.
- Frontend limits were added: **6 files**, **30MB per file**, **120MB total**.
- If a baseline/planned file is detected but actual data is missing, the mapping preview shows an **Additional actual data required** panel.
- The user can add actual/F-2/progress/forecast/workforce files from the same file picker and rerun preflight.

## Product rule

No actual data → no comparison result.
Unclear actual data → needs confirmation.
Confirmed actual data → calculate dashboard.
