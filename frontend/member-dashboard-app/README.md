# DevBareun Member Dashboard App

React/Vite workspace for the authenticated DevBareun customer panel.

This app is intentionally separate from the public static marketing website in `frontend/`.

## Purpose

- Keep the landing page stable and static.
- Move authenticated workspace flows into a component-based app.
- Use backend APIs with `credentials: "include"` so production auth can use HTTP-only cookies.
- Avoid storing access tokens in browser storage.

## Commands

```powershell
npm install
npm run dev
npm run build
```

## Production Direction

When this app replaces the static workspace pages, deploy it as the workspace frontend or build it into a routed subfolder such as `/workspace/`.
