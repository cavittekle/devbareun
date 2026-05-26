# DevBareun v1.2.9 — Processing Experience UI

## Scope
Dashboard-style processing experience for customer file upload and analysis result generation.

## Added
- DevBareun Processing Center panel during upload/preflight/analyze flow.
- Dashboard-style progress, status steps, file pills, package name and backend endpoint display.
- PDF-specific processing status: PDF text extraction and document review queued.
- Dashboard generation status during result calculation.
- Dark/light mode responsive CSS for processing panel.

## Changed files
- frontend/js/backend-integration.js
- frontend/css/styles.css
- backend/app/version.py
- AGENTOPS_RELEASE_MANIFEST.json

## QA
- node --check frontend/js/backend-integration.js: PASS
- python compile backend/app/version.py: PASS

## Version
1.2.9-processing-experience-ui
