# DevBareun API Documentation

## Purpose

This document defines backend API behavior for DevBareun.

Keep this file updated whenever endpoints, request formats, response formats, auth rules, uploads, analysis jobs, payments, or reports change.

## Base URLs

Development:

```text
http://localhost:8000
```

Production:

```text
https://devbareun-production.up.railway.app
```

Update this if the backend is later moved behind a dedicated API domain.

## Authentication

Recommended format:

```http
Authorization: Bearer <access_token>
```

Protected endpoints must validate the user.

Admin endpoints must validate admin role.

## Standard Success Response

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

## Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

Do not expose internal stack traces in production.

## Health

### GET `/api/health`

Purpose: Check backend availability.

Authentication: Not required.

Response:

```json
{
  "status": "ok",
  "service": "devbareun-backend"
}
```

## Authentication API

### POST `/api/auth/register`

Purpose: Register new user.

Request:

```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "name": "User Name"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com"
  }
}
```

### POST `/api/auth/login`

Purpose: Login user.

Request:

```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "access_token": "token",
    "refresh_token": "token",
    "user": {}
  }
}
```

### POST `/api/auth/logout`

Purpose: Logout user.

Authentication: Required.

## Projects API

### GET `/api/projects`

Purpose: List user projects.

Authentication: Required.

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Project name",
      "status": "active",
      "created_at": "ISO_DATE"
    }
  ]
}
```

### POST `/api/projects`

Purpose: Create project.

Authentication: Required.

Request:

```json
{
  "name": "Project name",
  "description": "Optional description",
  "location": "Optional location",
  "contractor": "Optional contractor"
}
```

### GET `/api/projects/{project_id}`

Purpose: Get project details.

Authentication: Required.

Authorization: User must own the project or have access.

### PATCH `/api/projects/{project_id}`

Purpose: Update project.

Authentication: Required.

Authorization: User must own the project or have access.

### DELETE `/api/projects/{project_id}`

Purpose: Delete or archive project.

Authentication: Required.

Authorization: User must own the project or have access.

## Upload API

### POST `/api/projects/{project_id}/files`

Purpose: Upload construction project files.

Authentication: Required.

Supported direction:

- `.xlsx`
- `.csv`
- `.pdf`
- `.xml`
- `.xer`

Request type:

```text
multipart/form-data
```

Fields:

```text
files[]
analysis_type
language
```

Response:

```json
{
  "success": true,
  "data": {
    "uploaded_files": [
      {
        "id": "uuid",
        "filename": "schedule.xlsx",
        "file_type": "xlsx",
        "status": "uploaded"
      }
    ]
  }
}
```

Validation:

- reject unsupported file types
- reject oversized files
- reject unauthenticated uploads
- store private files with user/project ownership

### DELETE `/api/files/{file_id}`

Purpose: Delete uploaded file before analysis.

Authentication: Required.

Authorization: User must own file/project.

## Analysis API

### POST `/api/projects/{project_id}/analyze`

Purpose: Start analysis job.

Authentication: Required.

Request:

```json
{
  "analysis_type": "full_project_control",
  "file_ids": ["uuid"],
  "language": "en"
}
```

Allowed analysis types:

```text
schedule_analysis
cost_analysis
progress_payment_analysis
workforce_analysis
material_stock_analysis
risk_analysis
full_project_control
```

Response:

```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "queued"
  }
}
```

### GET `/api/analysis-jobs/{job_id}`

Purpose: Get job status.

Authentication: Required.

Response:

```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "completed",
    "progress": 100,
    "result_id": "uuid"
  }
}
```

Possible statuses:

```text
uploaded
queued
parsing
analyzing
completed
failed
cancelled
```

### GET `/api/analysis-results/{result_id}`

Purpose: Get analysis result JSON.

Authentication: Required.

Response:

```json
{
  "success": true,
  "data": {
    "result_id": "uuid",
    "project_id": "uuid",
    "summary": {},
    "metrics": {},
    "risks": [],
    "recommendations": [],
    "dashboard_blocks": [],
    "confidence_score": 0.85,
    "missing_fields": [],
    "warnings": []
  }
}
```

## Reports API

### POST `/api/analysis-results/{result_id}/reports`

Purpose: Generate PDF or Excel report.

Authentication: Required.

Request:

```json
{
  "format": "pdf",
  "language": "en",
  "paper_size": "A4"
}
```

Allowed formats:

```text
pdf
excel
```

Allowed paper sizes:

```text
A4
A3
```

Response:

```json
{
  "success": true,
  "data": {
    "report_id": "uuid",
    "download_url": "signed-url",
    "expires_at": "ISO_DATE"
  }
}
```

### GET `/api/reports/project/{project_id}`

Purpose: List report archive metadata for a project the current user owns. New
reports expose `snapshot_available`, `snapshot_version`, checksum metadata and
download audit fields; raw report payload is never returned by this endpoint.

Authentication: Required.

### POST `/api/reports/generate/{project_id}`

Purpose: Generate a PDF or Excel report from the latest completed analysis and
store a frozen report snapshot.

Body:

```json
{
  "report_format": "pdf",
  "report_type": "Project Control Report"
}
```

`report_format` accepts `pdf`, `excel`, or `xlsx`.

Authentication: Required.

### GET `/api/reports/{report_id}/download`

Purpose: Download a user-authorized report. The response is rendered from the
stored snapshot where available and returns private no-store headers.

Authentication: Required.

## Usage and Plans API

### GET `/api/usage`

Purpose: Show current usage and remaining project credits.

Authentication: Required.

Response:

```json
{
  "success": true,
  "data": {
    "plan": "plus",
    "monthly_limit": 5,
    "used_this_month": 2,
    "remaining": 3
  }
}
```

### GET `/api/plans`

Purpose: List available plans.

Authentication: Not required.

## Payment API

### POST `/api/payments/checkout`

Purpose: Create checkout session.

Authentication: Required.

Request:

```json
{
  "plan": "plus"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "checkout_url": "https://..."
  }
}
```

### POST `/api/payments/webhook`

Purpose: Receive payment provider webhook.

Authentication: Not required.

Security: Must verify webhook signature.

## Admin API

All admin endpoints require admin role.

### GET `/api/admin/users`

Purpose: List users.

### GET `/api/admin/projects`

Purpose: List projects.

### GET `/api/admin/analysis-jobs`

Purpose: Inspect jobs.

### GET `/api/admin/failed-uploads`

Purpose: Inspect failed uploads.

### GET `/api/admin/payments`

Purpose: Inspect payments.

## API Security Rules

- Validate every request.
- Protect user-owned resources.
- Protect admin routes.
- Verify payment webhooks.
- Do not expose secret keys.
- Do not expose internal error traces.
- Use signed URLs for private files and reports.
- Apply rate limiting to public endpoints.


## Analysis worker operations (staff only)

```text
GET /api/analysis/operations
```

Returns secret-safe queue counts and worker liveness. Requires an owner/staff authenticated user. It never returns customer analysis payloads or storage paths.


### Failed/dead-letter recovery (staff only)

```text
GET  /api/analysis/operations/recovery-jobs?limit=50
POST /api/analysis/operations/jobs/{job_id}/retry
```

The retry request accepts `{ "reset_attempts": true|false }`. A dead-lettered job requires `true`; the API rejects any job that already has a persisted result.


## Audit archive operations (v1.4.25)

These endpoints require the Super Admin `audit` capability. The retry endpoint is additionally restricted to `owner`. Responses never contain audit archive webhook URLs, HMAC secrets or outbox payload bodies.

```text
GET  /api/super-admin/audit-archive
POST /api/super-admin/audit-archive/{archive_id}/retry
```

A dead-lettered archive delivery requires `{ "reset_attempts": true }` for explicit requeue.

## Operational health (owner/operator only)

### GET `/api/operations/health`

Returns a staff-safe aggregate of runtime readiness, analysis worker state and audit archive delivery state. It is limited to `owner` and `operator` roles through the `operations` capability. The response contains incident codes and counts only; it never exposes customer records, signed URLs, webhook URLs, or secrets.

### GET `/api/super-admin/operations-health`

Super Admin panel alias for the same staff-safe health summary. The browser panel uses this endpoint for the **Operations health** tab.



## Company workspace API

Company roster management is authenticated and deliberately separate from project access.

```text
GET   /api/company/workspace
POST  /api/company/workspace
POST  /api/company/invitations
POST  /api/company/invitations/accept
POST  /api/company/invitations/{invitation_id}/revoke
PATCH /api/company/members/{membership_id}
```

Invitation delivery is manual in v1.4.32. The response shows a one-time URL; DevBareun stores only a SHA-256 token digest. Company membership does not itself grant cross-user access to projects, uploads, analyses or reports.


## Explicit Project Sharing (v1.4.33)

- `GET /api/project-access/projects` — owned plus explicitly shared projects.
- `GET /api/project-access/{project_id}/members` — access roster; owner/project manager only.
- `POST /api/project-access/{project_id}/members` — grant access to an active company member.
- `PATCH /api/project-access/{project_id}/members/{grant_id}` — change role or revoke status.
- `DELETE /api/project-access/{project_id}/members/{grant_id}` — revoke access.
