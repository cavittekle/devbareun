# DevBareun Frontend Architecture

DevBareun uses a static public website and a React/Vite customer workspace.

## Public Website

Source of truth:

- `frontend/index.html`
- `frontend/css/modern-landing.css`
- `frontend/js/modern-landing.js`

Deploy target:

- Vercel Root Directory: `frontend`

Rules:

- Keep the public website static, fast, and dark/cyan branded.
- Public copy must stay construction-focused and must not mention AI wording.
- Public payment wording must point to Lemon Squeezy.
- Do not add dashboard-only logic to the landing page.

## Customer Workspace

Source of truth:

- `frontend/member-dashboard-app/`
- Generated deploy output: `frontend/workspace/`

The React/Vite workspace app is the source for authenticated customer screens. `npm run build` from `frontend/` builds it into `/workspace/` for Vercel while keeping the static public website in place.

React workspace views include:

- login
- register
- overview
- upload
- projects
- reports
- billing
- settings
- checkout status
- payment success/failure status

Retired static workspace pages:

- `/dashboard.html`
- `/upload.html`
- `/projects.html`
- `/project-detail.html`
- `/reports.html`
- `/billing.html`
- `/settings.html`
- `/login.html`
- `/register.html`
- `/checkout.html`
- `/payment-success.html`
- `/payment-failed.html`

These routes are redirected to `/workspace/` or a matching `?view=` state in `frontend/vercel.json`.

Rules:

- Use HTTP-only cookie sessions through backend routes.
- Do not store access tokens in localStorage.
- Show empty states until real user data exists.
- Upload files through signed storage URLs, then mark uploads as complete through the backend.
- Show only dashboard sections supported by uploaded and parsed data.

## API Boundary

Frontend owns:

- page layout
- package selection
- upload progress display
- empty states
- user navigation

Backend owns:

- Supabase Auth validation
- signed upload/download URLs
- project ownership checks
- parser jobs
- dashboard/result generation
- report generation
- Lemon Squeezy checkout and webhooks
- credits and billing rules

## Migration Checklist

1. Keep static landing as-is.
2. Build and test `frontend/member-dashboard-app`.
3. Wire React workspace to real upload and report endpoints.
4. Keep legacy HTML workspace routes redirected to `/workspace/`.
5. Keep legacy HTML auth/payment URLs as redirect shells only.

## Vercel Build

From `frontend/`:

```powershell
npm run build
```

This command:

1. Installs `member-dashboard-app` dependencies with `npm ci`.
2. Builds the React workspace with Vite.
3. Copies the generated app into `frontend/workspace/`.

`frontend/workspace/` is generated output and is not committed.
