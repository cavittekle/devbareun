# DevBareun v1.2.12 — Share Link Active

## Fix
- Activated the result dashboard Share Link button.
- Generates a clean shareable URL using the current result `project_id`.
- Copies the link to clipboard on desktop.
- Uses native Web Share API on supported mobile browsers.
- Adds a DevBareun-style toast confirmation in dark and light mode.

## Changed files
- frontend/result-dashboard.html
- frontend/js/result-dynamic.js
- frontend/css/result-dashboard.css
- backend/app/version.py
- AGENTOPS_RELEASE_MANIFEST.json
