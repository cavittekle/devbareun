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

## Environment

Use `.env.example` only as a public Vercel reference. Do not add backend secrets to Vercel.

Allowed frontend values:

- `VITE_PUBLIC_SITE_URL`
- `VITE_API_BASE_URL`
- `VITE_API_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Forbidden frontend values:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`
