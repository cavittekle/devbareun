# DevBareun Project State

## Project Overview

Project name: DevBareun

Project type: Construction analytics, project control, reporting, and management dashboard SaaS platform.

Main goal: Allow users to upload construction project data and receive structured project control dashboards, reports, risk summaries, schedule/cost analysis, and exportable PDF/Excel outputs.

Current status: **v1.4.0 Production SaaS Core** (2026-07-27)

- Frontend: static HTML/CSS/JS in `frontend/` (Vercel root: `frontend`)
- Backend: FastAPI in `backend/` (Railway root: `backend`)
- Database: Supabase PostgreSQL with RLS in `database/`
- Payment: Lemon Squeezy checkout (Single / Plus / Pro)
- Landing: dark/cyan DevBareun design with 4 public packages
- Legacy `frontend/public/` and `frontend/workspace/` are untracked and excluded from deploys

## Approved Product Direction

DevBareun should be a professional SaaS platform for construction project analytics and reporting.

Approved direction:

- English default language
- Azerbaijani secondary language
- dark-only public landing experience
- clean cyan/blue branding
- mobile-first responsive interface
- orbit-logo loading screen
- public landing page
- upload section
- pricing section
- customer dashboard after login
- executive construction dashboard
- report archive
- PDF/Excel export
- Supabase + Vercel + Railway + GitHub stack direction

## Public Copy Restrictions

Do not use these words in public website copy:

- AI
- artificial intelligence
- suni intellekt
- intelligence
- intellekt

Use these alternatives:

- construction analytics
- project control
- management dashboard
- risk analytics
- schedule analytics
- cost analytics
- document control
- reporting
- executive dashboard
- project performance analytics

## Technology Stack

Frontend:

- Current framework: static HTML/CSS/JS in `frontend/`
- Styling system: custom dark/cyan DevBareun CSS, led by `frontend/css/modern-landing.css`
- Language system: EN default with AZ secondary language support in `frontend/js/modern-landing.js`
- Deployment platform: Vercel

Backend:

- Current framework: FastAPI in `backend/app/`
- Runtime: Python 3.12 on Railway
- Deployment platform: Railway

Database/Auth/Storage:

- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage

Payments:

- Payment provider abstraction
- Lemon Squeezy is the current checkout provider
- Lemon Squeezy is the active payment provider
- Do not hardcode payment business logic only to one provider

Repository:

- GitHub

## Existing Main Features

- Landing page: `frontend/index.html`
- Dashboard/result pages: static member pages in `frontend/`, backed by dynamic backend dashboard/report routes
- Upload UI: public guided upload/package section and protected upload route direction
- Pricing UI: Lemon Squeezy-oriented Single / Plus / Pro plan direction
- Language switcher: EN/AZ public landing toggle
- Dark-only public UI: approved dark/cyan DevBareun landing experience
- Loading screen: compact white DevBareun orbit-logo loader
- Authentication: Supabase-oriented auth routes and runtime helpers
- Backend API: FastAPI routes under `backend/app/`
- Database: Supabase SQL and RLS files in `database/`
- Export: PDF/Excel report direction through backend report services
- Admin panel: frontend admin page plus backend/admin workspace direction

## Features In Progress

- SaaS authentication
- Supabase schema and RLS
- Upload engine
- Parser improvements
- Dynamic dashboard generation
- PDF/Excel export
- Payment and usage limits
- Admin panel
- Security hardening
- CI/CD

## Known Bugs

Add bugs here with date and status.

Example format:

```text
YYYY-MM-DD - Bug title
Status: open / fixed / needs review
Files likely affected:
Notes:
```

Current known bugs:

- 
- 
- 

## Do Not Replace

Do not replace:

- approved logo direction
- existing project structure unless required
- existing main pages if they can be improved
- existing dashboard direction
- existing footer style
- existing language system
- existing upload/pricing structure
- existing deployment setup unless required

## Current Priorities

1. Stabilize existing frontend.
2. Complete EN/AZ localization.
3. Add authentication without forcing login on first page.
4. Add Supabase schema and RLS.
5. Add upload engine.
6. Improve parser reliability.
7. Build modular analytics.
8. Generate dynamic dashboards.
9. Add PDF/Excel export.
10. Add payment and plan limits.
11. Add admin panel.
12. Harden security.
13. Prepare deployment.

## Dashboard Requirements

Dashboard should be dynamic and show only relevant sections.

Allowed sections:

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
- Export Buttons

Do not show:

- empty cards
- placeholder charts
- fake KPIs
- duplicated sections
- Ref errors
- unrelated analytics blocks

## Upload and Parser Requirements

Supported upload direction:

- Excel `.xlsx`
- CSV
- PDF partial support
- MS Project XML beta
- Primavera XER beta placeholder

Parser should detect:

- project name
- contractor
- contract value
- planned progress
- actual progress
- actual cost
- F-2/progress payment data
- schedule data
- workforce data
- material stock data
- risk items
- building/block names

Parser must return:

- normalized JSON
- confidence score
- missing fields
- warnings

Do not fake missing values.

## SaaS Plan Direction

Plans:

- Guest: one-time project analysis
- Plus: limited monthly project analyses
- Pro: higher monthly project analyses

Required logic:

- track usage
- show remaining credits
- block analysis when limit is reached
- keep payment provider separate from plan/usage logic

## Security Requirements

Never expose:

- Supabase service role key
- JWT secret
- database password
- payment secret
- private storage keys
- production credentials

Frontend may only use public-safe variables.

Private routes and admin routes must be protected.

Database should use user ownership and RLS where applicable.

## Latest Accepted State

Update this section after every major accepted change.

Date: 2026-09-19

Accepted version/package: v1.4.0 Production SaaS Core

Accepted frontend state: static `frontend/` deployment root, dark/cyan landing, EN/AZ toggle, four public analysis packages.

Accepted backend state: FastAPI backend under `backend/`, with parser/analyzer guardrails and report/dashboard services.

Accepted deployment state: Vercel root is `frontend`; Railway root is `backend`; Supabase SQL remains in `database`.

Notes: Local artifacts, demo bundles, build outputs, and duplicate legacy folders are excluded from source control and deploy packages.
