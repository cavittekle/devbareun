# Company Team Foundation — v1.4.32

This release introduces a controlled company roster and manual invitation workflow.

## Scope

- One company workspace per user profile under the existing `users_profile.company_id` model.
- Company roles: `owner`, `manager`, `editor`, `viewer`.
- Owners and managers can create invitations, revoke pending invitations and update non-owner members.
- Invitation URLs are generated only once. DevBareun stores a SHA-256 token digest, never the raw token.
- Invitation acceptance requires an active session with the exact invited email address.
- An account already linked to another company workspace cannot accept a second-company invitation.
- Changes are audit-event candidates and use the existing audit service/outbox path where configured.

## Manual invite delivery

This release intentionally uses manual invite delivery. The manager copies the one-time URL and transmits it through an approved channel. No email provider, SMTP credential or raw invitation token is persisted by DevBareun.

```text
https://devbareun.com/workspace/?view=team&invite=<one-time-token>
```

The raw URL cannot be recovered after the invite response is dismissed. Revoke it and create a new invitation when necessary.

## Deliberate authorization boundary

Company membership **does not yet grant cross-user access** to projects, uploads, analyses or reports. Existing project ownership/RLS rules remain unchanged in v1.4.32.

A later project-sharing phase must introduce an explicit project access matrix and migration. This prevents an invitation from unintentionally exposing all historical company data.

## Deploy order

Run after `2026_06_21_v1431_billing_lifecycle_integrity.sql`:

```text
2026_06_21_v1432_company_team_foundation.sql
```

## Endpoints

```text
GET   /api/company/workspace
POST  /api/company/workspace
POST  /api/company/invitations
POST  /api/company/invitations/accept
POST  /api/company/invitations/{invitation_id}/revoke
PATCH /api/company/members/{membership_id}
```

## Operational checks

- Confirm `company_memberships` and `company_invitations` are present after migration.
- Confirm the raw invite token is absent from database rows and audit metadata.
- Test owner invite, invited-email acceptance, wrong-email rejection, revoke and expiry.
- Keep project authorization checks unchanged until the next explicit project sharing release.
