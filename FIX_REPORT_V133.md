# DevBareun v1.3.3 — Protected Dashboard + Project History UI

## Purpose
This release connects the SaaS foundation to visible frontend workflows without replacing the existing DevBareun design language.

## Added
- Protected workspace style pages for Login, Register, Dashboard, Projects, Upload, Reports, Billing, Profile, Settings, Admin and Guest Result.
- SaaS UI shell preserving cyan/blue enterprise branding.
- User session indicator using stored Supabase session / owner email.
- Project creation UI with Project ID history.
- Upload UI with visible file names, size/type metadata and per-file remove actions.
- Analysis record creation UI linked to Project ID, File IDs and control package.
- Billing UI for Single Project, Plus and Pro.
- Credit status panel.
- Reports / analysis history UI.
- Admin overview UI.
- Profile and company identity form.

## Files changed
- frontend/css/saas-ui.css
- frontend/js/saas-ui.js
- frontend/login.html
- frontend/register.html
- frontend/dashboard.html
- frontend/projects.html
- frontend/upload.html
- frontend/reports.html
- frontend/billing.html
- frontend/checkout.html
- frontend/profile.html
- frontend/settings.html
- frontend/admin.html
- frontend/guest-result.html
- backend/app/version.py
- AGENTOPS_RELEASE_MANIFEST.json

## Test summary
- node --check frontend/js/saas-ui.js: PASS
- node --check frontend/js/supabase-saas-client.js: PASS
- python compile backend/app/version.py: PASS

## Expected health version
1.3.3-protected-dashboard-project-history-ui
