# DevBareun Full Package v0.5.7

Includes:

- Frontend v0.5.6 deploy/preflight UI fix
- Backend v0.5.7 PDF dashboard metric fix

Frontend deploy target: `construction-dashboard` repo / Vercel or Netlify.

Backend deploy target: `devbareun-backend` repo / Railway.

Backend health version expected after Railway deploy:

```text
0.5.7-pdf-dashboard-metric-fix
```

Railway custom start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Pre-deploy command should remain empty.
