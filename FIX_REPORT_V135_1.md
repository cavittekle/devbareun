# DevBareun v1.3.5.1 — Auth Router Activation Fix

## Fixed
- Connected `backend/app/auth_routes.py` into `backend/app/main.py`.
- `/api/auth/pilot-login` and `/api/auth/me` now become active backend routes.
- Removed `EmailStr` dependency from auth route model to avoid requiring `email-validator` in Railway runtime.

## Version
This is a corrected v1.3.5 full package.
