# DevBareun v1.3.5 — Real Auth + Protected Workspace

## Scope
This patch adds visible frontend authentication and protected workspace behavior while preserving the existing DevBareun design language.

## Added
- Login page
- Register page
- Protected dashboard page
- Projects page shell
- Reports page shell
- Billing page shell
- Profile page shell
- Auth workspace JS
- Pilot auth backend routes
- Supabase-compatible token verification helper
- Header auth controls
- User menu, plan badge and credit badge
- Protected route redirect logic

## Production note
Pilot login is included so the workspace can be tested before Supabase Auth keys are configured. Production should use Supabase Auth JWTs through the same `/api/auth/me` validation path.
