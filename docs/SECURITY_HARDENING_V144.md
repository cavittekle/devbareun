# DevBareun v1.4.4 Security Hardening

Date: 2026-06-18

## Scope

This release tightens browser-session security without changing the canonical project/upload/analysis API introduced in v1.4.2.

## Backend changes

- Added cookie-authenticated request integrity checks in `backend/app/security_runtime.py`.
- State-changing requests carrying the `devbareun_auth` HTTP-only cookie now require a trusted `Origin` or `Referer` in production security mode.
- Added double-submit CSRF protection using:
  - cookie: `devbareun_csrf`
  - header: `X-CSRF-Token`
- CSRF validation is controlled by `DEVBAREUN_REQUIRE_CSRF_TOKEN`; production default is enabled.
- Payment webhook paths are excluded from CSRF checks so server-to-server webhook delivery is not blocked.
- Login and pilot-login set a fresh CSRF cookie together with the HTTP-only auth cookie.
- Logout clears both auth and CSRF cookies.
- Added `GET /api/auth/csrf` for clients that need to initialize or refresh the CSRF cookie before a mutating request.

## Frontend changes

- React workspace API client now automatically reads `devbareun_csrf` and sends `X-CSRF-Token` for unsafe HTTP methods.
- Static `frontend/js/devbareun-api.js` does the same for legacy/static flows that still use the shared API helper.
- Production static frontend no longer supports the `devbareun_allow_local_token_storage` override. Production auth must rely on backend-managed HTTP-only cookies, not persisted bearer tokens.

## Operational notes

Production environment should include:

```env
DEVBAREUN_PRODUCTION_SECURITY=true
DEVBAREUN_REQUIRE_CSRF_TOKEN=true
DEVBAREUN_ALLOWED_ORIGINS=https://devbareun.com,https://www.devbareun.com,https://devbareun.vercel.app
```

Deploy backend and frontend together. Older frontend clients that do not send `X-CSRF-Token` will receive `403 csrf_failed` for cookie-authenticated POST/PATCH/PUT/DELETE calls when `DEVBAREUN_REQUIRE_CSRF_TOKEN=true`.

## Verification

Run from the repository root:

```bash
python -m compileall -q backend/app agents/devbareun_ops_engine
cd backend && pytest -q
cd ../frontend/member-dashboard-app && npm ci && npm run build
```
