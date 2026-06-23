# Super Admin and Customer Workspace

DevBareun uses two clear access areas:

- Customer workspace: `/workspace` or `/dashboard`
- Super Admin panel: `/super-admin`

The public frontend remains static HTML/CSS/JS in `frontend/`. The backend is FastAPI in `backend/`.

## Roles

Super Admin staff roles are stored in `users_profile.role`:

- `owner` - all modules and staff management
- `support` - customers, support tickets, notes, activity
- `analyst` - projects, uploads, reports, activity
- `finance` - payments, credits, activity
- `operator` - projects, reports, activity

Customer users should use `customer`. The older `user` and `admin` role names are accepted only for legacy compatibility; new production staff should use `owner`, `support`, `analyst`, `finance`, or `operator`.

## Permission Matrix

| Module | owner | support | analyst | finance | operator | customer |
| --- | --- | --- | --- | --- | --- | --- |
| Overview | yes | yes | yes | yes | yes | no |
| Customers | yes | yes | no | no | no | no |
| Projects | yes | no | yes | no | yes | no |
| Uploads | yes | no | yes | no | no | no |
| Reports | yes | no | yes | no | yes | no |
| Payments | yes | no | no | yes | no | no |
| Credits | yes | no | no | yes | no | no |
| Support | yes | yes | no | no | no | no |
| Activity | yes | yes | yes | yes | yes | no |
| Audit | yes | no | no | no | no | no |
| Staff management | yes | no | no | no | no | no |
| Analysis operations / recovery | yes | no | no | no | yes | no |

## First Owner Setup

1. Create the owner account in Supabase Auth.
2. Apply all SQL files from `database/SUPABASE_DEPLOY_ORDER.md`.
3. Promote the owner profile:

```sql
update public.users_profile
set role = 'owner', status = 'active'
where lower(email) = lower('owner@devbareun.com');
```

4. Set Railway:

```env
DEVBAREUN_ADMIN_EMAILS=owner@devbareun.com
DEVBAREUN_ALLOW_ADMIN_EMAIL_FALLBACK=false
DEVBAREUN_ALLOW_DEVBAREUN_DOMAIN_ADMINS=false
```

## Staff Users

Create staff from the Super Admin staff module or by inserting/updating `users_profile`.
Staff still need a valid Supabase Auth login. The backend checks the bearer token and then reads `users_profile.role`.

## Customer Workspace

Customers can:

- Register/login
- Create projects
- Upload project files
- Preview mapping
- Run analysis with credits or payment unlock
- Download their own reports
- View their own projects, reports, billing state and credit usage

Backend routes enforce owner checks. Customer requests must not include data owned by another email/user.

## Super Admin Modules

The Super Admin panel reads protected backend endpoints for:

- Customers
- Companies
- Projects
- Uploads
- Payments
- Reports
- Credits
- Support tickets
- Activity logs
- Audit logs
- Staff

Admin/staff actions are written to `audit_logs` when possible.

## Boundary rule

A staff label does not grant unrestricted customer-data access. Backend project, upload, analysis and report routes check the capability for their own resource area. Customer status endpoints cannot modify staff users; use the owner-only Staff module for staff role/status changes. See `PANEL_ACCESS_BOUNDARIES_V1423.md`.
