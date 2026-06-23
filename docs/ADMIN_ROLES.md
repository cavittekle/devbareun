# Admin Roles

DevBareun separates customer workspace access from staff and owner access.

## Roles

- `customer`: normal customer workspace user. Can access only their own projects, uploads, reports, billing state and credits.
- `owner`: full Super Admin access. Can manage staff, roles, credits, payments, customers, projects, reports, support and audit logs.
- `support`: customer support role. Can view customers, support tickets, notes and activity. Cannot view payments or manage staff.
- `analyst`: project analysis role. Can view projects, uploads, reports and activity.
- `finance`: billing role. Can view payments, credits and activity. Cannot manage staff.
- `operator`: operations role. Can view projects, reports and activity.

## Legacy Compatibility

The old `admin` role is normalized as `owner` in the backend for old rows only. New production staff accounts must use `owner`, `support`, `analyst`, `finance`, or `operator`.

## Access Rules

- Customer users must not access `/super-admin` API data.
- Every `/api/super-admin/...` route must be protected by backend role checks.
- Frontend menu hiding is only a usability layer; backend authorization is required.
- Staff management and role changes are owner-only.

