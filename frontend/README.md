# DevBareun Frontend

Production frontend target for Vercel.

## Deploy

- Vercel Root Directory: `frontend`
- Config file: `vercel.json`
- Entry page: `index.html`
- Ignore rules: `.vercelignore`

Do not deploy the repository root. The root has no production `index.html`.

## Local Run

```powershell
cd frontend
python -m http.server 4173
```

Open `http://127.0.0.1:4173/index.html`.

## Runtime Model

This frontend is static HTML/CSS/JS. Backend API calls resolve through `js/devbareun-api.js` and default to:

```text
https://devbareun-production.up.railway.app
```

For local backend testing, set this in the browser console or local storage:

```js
localStorage.setItem("devbareun_use_local_backend", "true")
```

## Customer Workspace App

The framework-based customer workspace is in `member-dashboard-app/`.

```powershell
cd member-dashboard-app
npm install
npm run dev
```

To build the workspace into the Vercel-served `/workspace/` route:

```powershell
npm run build
```

The generated `workspace/` directory is build output and should not be committed.

Retired workspace HTML routes such as `/dashboard.html`, `/upload.html`, `/projects.html`, `/reports.html`, `/billing.html`, and `/settings.html` redirect to `/workspace/` through `vercel.json`.

## Environment

Use `.env.example` only as a public Vercel reference. Do not add backend secrets to Vercel.

Allowed frontend values:

- `VITE_PUBLIC_SITE_URL`
- `VITE_API_BASE_URL`
- `VITE_API_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Forbidden frontend values:

- backend-only private keys
- webhook secrets
- service role keys
- JWT secrets
- database passwords
- Redis tokens
- payment API keys
