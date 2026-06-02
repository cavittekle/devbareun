# DevBareun v1.1.7 — Approved Upload Wizard Design

## Purpose
Applies the approved dark/cyan upload wizard design selected by the user.

## Changed
- Rebuilt the homepage upload/analysis-selection section into a compact 3-step wizard.
- Moved analysis type cards and upload area into one unified panel.
- Added centered analysis card row, integrated drag/drop upload zone, supported-format chips, collapsible data requirements, and bottom action bar.
- Preserved existing backend integration IDs: `analysisTypeGrid`, `dropZone`, `fileInput`, `fileList`, `generatePreviewBtn`, `clearFilesBtn`, `mappingPreviewPanel`, and requirements IDs.
- Added EN/AZ text keys for the new wizard structure.

## Files
- `frontend/index.html`
- `frontend/css/styles.css`
- `frontend/js/i18n-extended.js`

## Deployment
Upload the changed files to GitHub, commit, then allow Vercel to redeploy. If needed, run a manual Vercel redeploy and hard refresh the browser.
