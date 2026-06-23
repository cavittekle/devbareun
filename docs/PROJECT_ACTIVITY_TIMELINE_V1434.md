# Project Activity Timeline — v1.4.34

## Purpose

The Project Activity timeline gives project collaborators a read-only history of
safe operational events without exposing global audit records, request
credentials, storage paths, signed URLs or raw file payloads.

## Access model

`viewer`, `editor`, `manager` and implicit `owner` project roles can read the
timeline. Company membership alone does not grant access. No timeline endpoint
permits customer-side mutation.

## API

```text
GET /api/project-activity/{project_id}?limit=80
```

The limit is bounded to `1–200` and the route requires `project_activity`
project scope. Events include a public event ID, safe action/entity metadata,
actor type/email, and UTC occurrence time.

## Recorded events

New events include project-access grant changes, upload preparation/completion/
delete, analysis queue/completion/failure, and report generation/download.
Existing historical activity logs are not backfilled, so the timeline begins
when this migration is deployed.

## Storage and retention

Rows are append-only; direct update/delete is rejected by the database trigger.
The global `audit_logs` hash chain remains the authoritative owner/staff audit
trail. Project timeline records are collaboration-facing and should follow the
same project retention/soft-delete policy during a later approved purge job.

## Deployment

1. Apply `2026_06_21_v1434_project_activity_timeline.sql` after v1.4.33.
2. Deploy the Railway web and analysis-worker code together so background
   analysis completion events are written consistently.
3. Run `python tools/check_project_activity_timeline.py --root .` and the
   normal backend/frontend release checks.
