# v1.4.33 — Explicit Project Sharing

## Purpose

A company roster is not a project permission model. This release adds explicit,
project-scoped grants for active company members and keeps owner access implicit.

## Project roles

| Role | Allowed actions |
|---|---|
| `viewer` | Read project status, executive dashboard, analysis outputs and frozen reports. |
| `editor` | Viewer access plus project updates, uploads, analysis starts and report generation. |
| `manager` | Editor access plus project-access grant management. |
| `owner` | Implicit project creator/owner access, including delete. It is not stored as a grant. |

## Security invariants

- Company membership alone grants **no** project, file, report or analysis access.
- A grant is valid only when its project, company and active company membership agree.
- A grant cannot be created for the project owner.
- Viewer role cannot see raw upload inventory or upload/delete files.
- Only owner/explicit project manager can list, create, alter or revoke grants.
- Project deletion remains owner-only.
- All grant mutations create authorization audit events.

## API

```text
GET    /api/project-access/projects
GET    /api/project-access/{project_id}/members
POST   /api/project-access/{project_id}/members
PATCH  /api/project-access/{project_id}/members/{grant_id}
DELETE /api/project-access/{project_id}/members/{grant_id}
```

## Deployment

Apply `2026_06_21_v1433_project_sharing.sql` after the v1.4.32 company-team
migration. Existing projects are backfilled only when a deterministic
`users_profile.company_id` match exists; unlinked projects remain owner-only.
