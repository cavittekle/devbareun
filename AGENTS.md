# AGENTS.md

## Project Identity

DevBareun is a construction analytics and project-control SaaS platform.

Current production model:

- Public website: static HTML/CSS/JS in `frontend/`
- Backend API: FastAPI in `backend/`
- Database/Auth/Storage: Supabase
- Frontend deploy: Vercel with Root Directory `frontend`
- Backend deploy: Railway with Root Directory `backend`
- Payment direction: Lemon Squeezy
- Repository root is not a deploy target and should not contain a production `index.html`

Default public language is English. Azerbaijani is the secondary language.

## Product Language Rules

Public UI copy must not use:

- AI
- artificial intelligence
- intelligence
- machine learning
- GPT
- suni intellekt
- intellekt

Use construction SaaS wording instead:

- construction analytics
- project control
- management dashboard
- schedule analytics
- cost analytics
- risk analytics
- material continuity
- progress tracking
- executive dashboard
- construction reporting
- recovery actions
- data mapping

## Current Public Landing Design

The approved current landing page is the dark/cyan DevBareun design in:

- `frontend/index.html`
- `frontend/css/modern-landing.css`
- `frontend/js/modern-landing.js`

Preserve:

- dark-only public landing experience
- cyan/teal DevBareun styling
- header with Platform, Upload, Pricing, Reports, FAQ
- EN/AZ language toggle
- Login button to the right of language selection
- Start Analysis CTA
- compact white DevBareun loader logo: `frontend/assets/devbareun-logo-compact-white.svg`
- orbit-logo loading screen
- hero dashboard preview
- upload section
- pricing section
- dashboard preview section
- compact footer with `info@devbareun.com`

Do not replace the site with a new design system unless the user explicitly asks to redesign and confirms the direction.

## Current Public Analysis Packages

The public upload package selector currently has 4 packages:

- Schedule Recovery
- Cost Control
- Material Continuity
- Risk & Decisions

Do not re-add `Full Project Control` to the public upload package selector unless the user explicitly asks for it.

Dashboard logic must remain dynamic:

- Show only dashboard sections supported by uploaded data.
- Hide empty blocks.
- Avoid fake production KPIs.
- Keep the dashboard preview clearly labeled as an example output.

## Main Engineering Rule

Inspect first. Reuse existing code. Improve only what is needed.

Before editing:

1. Identify the exact file(s) controlling the requested change.
2. Check whether similar code, styles, routes, API endpoints, or docs already exist.
3. Keep the change scoped to the request.
4. Do not duplicate pages, CSS systems, JavaScript logic, endpoints, migrations, or config files.
5. Do not rename or move files unless necessary.
6. Do not remove working features without explicit instruction.

## Frontend Rules

The production frontend is static HTML/CSS/JS.

Primary files:

- `frontend/index.html` - public landing page
- `frontend/css/modern-landing.css` - current landing style system
- `frontend/js/modern-landing.js` - language toggle, package selector, upload feedback, mobile menu
- `frontend/assets/` - approved logos, icons, favicon, OG image
- `frontend/vercel.json` - Vercel config

When changing frontend:

- Preserve dark readability.
- Preserve responsive behavior.
- Check mobile around 360px, 390px, and 430px when layout changes.
- Avoid horizontal overflow.
- Keep EN/AZ switching working.
- Add `data-i18n` and translation strings for new visible landing text.
- Keep button, card, upload, loader, header, and footer styling consistent with `modern-landing.css`.
- Do not add social icons or placeholder social links.
- Do not add Stripe wording to public UI.
- Use Lemon Squeezy wording for checkout/payment references.

## Logo Rules

Approved current assets include:

- Loader logo: `frontend/assets/devbareun-logo-compact-white.svg`
- Header/footer symbol: `frontend/assets/devbareun-symbol-white.svg`
- Favicon: `frontend/assets/favicon.png`

If a user provides a new logo file, copy it into `frontend/assets/` and update only the relevant reference. Do not scatter external Desktop paths into HTML/CSS.

## Localization Rules

Default language: English.

Secondary language: Azerbaijani.

When adding visible public landing text:

- Add English copy in the markup.
- Add English and Azerbaijani keys in `frontend/js/modern-landing.js`.
- Keep terminology construction-focused.
- Avoid mixed-language UI in one state.

## Upload Experience Rules

The upload section should remain guided and understandable.

It should show:

- selected package
- required files
- expected outputs
- uploaded file names
- upload progress indication
- smart detection feedback
- mapping preview

Supported public file wording:

- Excel
- CSV
- PDF
- Primavera XER
- MS Project XML
- supporting images

Do not make the upload experience feel like a generic file drop. It must explain what result the user receives.

## Dashboard Rules

Dashboard outputs must be data-driven.

Allowed dashboard areas:

- Executive Summary
- Schedule Status
- Delay Analysis
- Cost Control
- F-2 / Progress Payment Trend
- Workforce Productivity
- Material Continuity
- Risk Heatmap
- Critical Activities
- Recovery Actions
- Decision Register
- PDF Export
- Excel Export

Do not show:

- empty cards
- fake production results
- placeholder-only charts
- duplicate dashboard sections
- unrelated analytics blocks
- visible Ref/undefined errors

Example dashboard previews on the public landing are allowed only when clearly presented as examples.

## Backend Rules

The backend is FastAPI under `backend/app/`.

Before creating backend code:

- Search for an existing route/service/module first.
- Keep route/controller logic separate from business logic when possible.
- Validate inputs.
- Return clear user-safe errors.
- Do not expose stack traces in production responses.
- Keep payment provider logic separate from plan, credit, subscription, and usage-limit logic.

Preferred backend separation:

- parser
- analytics
- risk engine
- report generator
- database
- auth
- API routes
- scheduler
- export logic
- payment logic

## Parser Rules

Parser behavior should be conservative.

Parser output should include:

- normalized JSON
- confidence score
- missing fields
- warnings
- detected project name
- detected contract value
- planned progress
- actual progress
- F-2 / progress payment data
- workforce data
- material stock data
- schedule data
- contractor name
- building/block names

Do not invent values when data is missing. Return warnings instead.

## SaaS And Payment Rules

Current SaaS direction:

- guest one-time Single Project analysis
- Plus monthly project credits
- Pro monthly project credits
- protected login/workspace
- report archive
- PDF export
- Excel export
- admin panel
- payment provider abstraction

Production checkout uses Lemon Squeezy.

Known variant IDs:

- Single Project: `1741208`
- Plus: `1741246`
- Pro: `1741254`

Do not hardcode secrets. Do not put Lemon Squeezy API keys or webhook secrets into frontend files.

Stripe-related public website files or references should not be added. If old Stripe references exist, remove them only when they are truly unused or the user asks for cleanup.

## Supabase And Security Rules

Frontend may only use public Supabase values:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Backend/Railway owns private values:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- storage bucket secrets
- payment API keys
- webhook secrets

Never commit:

- real `.env` files
- API keys
- service role keys
- database passwords
- JWT secrets
- private tokens
- payment secrets
- production credentials

Use `.env.example` only for variable names and safe placeholder values.

## Deployment Rules

Deploy roots:

- Vercel Root Directory: `frontend`
- Railway Root Directory: `backend`
- Supabase SQL: `database`

Do not deploy repository root.

Keep these docs aligned when deploy behavior changes:

- `README.md`
- `frontend/README.md`
- `backend/README.md`
- `docs/DEPLOYMENT_ROOTS.md`
- `docs/LIVE_DEPLOY_CHECKLIST.md`
- `docs/LIVE_SUPABASE_PAYMENT_CHECKLIST.md`

Expected live backend health after Supabase is configured:

```json
{
  "status": "ok",
  "database": "connected",
  "storage": "configured"
}
```

If health shows `database: not_configured` or `storage: not_configured`, live Supabase setup is incomplete.

## Testing Rules

After frontend changes, at minimum:

- Run `node --check frontend/js/modern-landing.js` if landing JS changed.
- Load `http://localhost:4173/index.html` when a local server is running.
- Check for console errors.
- Check desktop and one mobile viewport for layout/overflow when visual layout changes.

After backend changes, use available checks:

- `python -m compileall backend/app`
- `python -m pytest` if tests exist
- backend health check: `/api/health`
- SaaS health check: `/api/saas/health`

Do not claim tests passed if they were not run.

## Documentation Rules

Update docs when changes affect:

- deploy roots
- environment variables
- API behavior
- payment flow
- Supabase setup
- upload flow
- dashboard behavior
- auth or security
- report export behavior

Keep documentation practical and short.

## Task Discipline

Every task must be small and focused.

Do not:

- refactor unrelated areas
- redesign the entire website for a small copy/layout request
- add unrelated sections
- add duplicate files
- change branding without explicit instruction
- remove current upload/package behavior unless requested
- add placeholder production content

## Required Output After Each Task

Report:

1. Files changed
2. What changed
3. What was tested
4. What was not changed
5. Any remaining risk or follow-up

## Final Rule

Inspect first.

Reuse existing code.

Keep DevBareun dark/cyan, construction-focused, and production-safe.

Do not duplicate.

Do not guess.
