# DevBareun v1.3.9.1 — Landing SaaS Hotfix

## Reason
The v1.3.9 Production Security package added backend/security improvements, but the public landing page did not visibly expose the SaaS customer flow: Login, Create account, package selection and payment package entry points.

## Fixed

### Landing page
- Added visible `Login`, `Create account` and authenticated `Workspace` controls to the header.
- Added mobile menu entries for Login, Create account, Workspace and Reports.
- Added hero package strip for:
  - Single Project
  - Plus — 5 projects/month
  - Pro — 20 projects/month
- Added SaaS access flow section:
  - Account
  - Payment package
  - Upload & dashboard
  - Report archive
- Rebuilt the pricing section as three customer-facing payment package cards.
- Package buttons now route to register/login/billing with selected plan preserved.

### Billing flow
- Billing page cards now receive selected plan state from the landing page.
- `billing-gate.js` highlights the selected plan and stores the selected plan in local storage.

### Auth flow
- Login/register plan select is prefilled from `?plan=` or the selected landing package.
- Register now respects `?next=` so package selection can continue directly to Billing.

## New files
- `frontend/css/landing-saas-v139.css`
- `frontend/js/landing-saas-v139.js`

## Modified files
- `frontend/index.html`
- `frontend/billing.html`
- `frontend/js/auth-workspace.js`
- `frontend/js/billing-gate.js`
- `frontend/css/persistent-workspace.css`

## QA
- Landing page contains 3 visible payment package cards.
- Landing page includes Login/Create account/Workspace links.
- Package CTA stores selected plan and redirects to Register or Billing.
- JS syntax checks passed for landing, auth and billing scripts.
