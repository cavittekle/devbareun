# DevBareun v1.3.9.2 — Landing Login Block Hotfix

## Purpose
The previous landing SaaS hotfix added login/register links and pricing/payment package flow, but the landing page still did not show a clear, visible login section. This hotfix adds a real workspace login block directly to the landing page hero area.

## Updated files
- `frontend/index.html`
- `frontend/css/landing-saas-v139.css`
- `frontend/js/landing-saas-v139.js`
- `AGENTOPS_RELEASE_MANIFEST.json`

## Added UI
- Visible hero login card on the landing page
- Email field
- Password field
- Package selector: Single Project / Plus / Pro
- Login to workspace button
- Create account link
- Forgot password link
- Authenticated workspace card for logged-in users
- Responsive mobile layout
- EN/AZ translations for the new block

## Expected behavior
- Guest users see the login card in the hero section.
- Authenticated users see an active workspace card instead.
- The login form uses the existing `auth-workspace.js` flow.
- The selected package is stored and carried into billing/register flow.

## Notes
This is a UI hotfix before v1.4.0 Real SaaS Launch Package. It does not replace the production security work from v1.3.9.
