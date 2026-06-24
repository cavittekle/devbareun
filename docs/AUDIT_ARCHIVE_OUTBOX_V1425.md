# Audit Archive Outbox v1.4.25

## Purpose

v1.4.25 adds a **transactional audit archive outbox** after the v1.4.24 append-only internal audit chain. Every new `integrity_version=1` audit event is snapshotted into `audit_archive_outbox` in the same database transaction. A separate Railway worker delivers that immutable snapshot to a configured HTTPS webhook.

This strengthens recoverability and external evidence retention. It does **not** prove that the remote receiver is immutable. The operator must select, secure and retain an archive destination independently.

## Data handling

The external snapshot includes audit identity, chain hashes, actor/action metadata, redacted metadata, request ID and timestamps. It intentionally excludes:

- bearer tokens, cookies, passwords, API keys and service-role secrets;
- raw request bodies;
- raw IP address and user-agent values;
- webhook credentials and response bodies.

The database stores `payload_sha256` and does not permit snapshot fields to be edited after insertion.

## Delivery behavior

Set these Railway-only variables on web, analysis-worker and audit-archive-worker services:

```env
DEVBAREUN_AUDIT_ARCHIVE_MODE=webhook
DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL=https://archive.example.com/devbareun/audit
DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET=<backend-only-HMAC-secret>
DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS=8
DEVBAREUN_AUDIT_ARCHIVE_BATCH_SIZE=25
DEVBAREUN_AUDIT_ARCHIVE_LEASE_SECONDS=90
DEVBAREUN_AUDIT_ARCHIVE_TIMEOUT_SECONDS=10
DEVBAREUN_AUDIT_ARCHIVE_WORKER_INTERVAL=15
```

Each POST uses a JSON body and:

```text
X-DevBareun-Audit-Timestamp: unix seconds
X-DevBareun-Audit-Event-ID: audit event id
X-DevBareun-Audit-Signature: v1=<hex hmac sha256(timestamp + "." + raw body)>
```

The receiving service must verify the timestamp, recompute the HMAC over the exact raw request body and deduplicate by `audit_id`/`event_hash`. A `2xx` response is considered delivered. No response body is stored.

Failures use bounded exponential retry. When attempts reach `DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS`, the item becomes `dead_lettered` (dead-lettered). It is not automatically reset.

## Worker deployment

Create a third Railway service with `Root Directory = backend` and config file `backend/railway.audit-archive.json`:

```bash
python -m app.audit_archive_worker --loop --interval 15 --batch-size 25
```

The worker uses the Supabase service role. Do not deploy its webhook URL or HMAC secret to Vercel.

## Operations

Owners and staff with the `audit` capability can read:

```text
GET /api/super-admin/audit-archive
```

Only the `owner` role can manually retry a reviewed item:

```text
POST /api/super-admin/audit-archive/{archive_id}/retry
{
  "reset_attempts": true
}
```

Do not retry a delivery until the archive destination, signature verification and idempotency behavior have been checked. The retry action itself is recorded in the audit chain and becomes a new archive outbox item.
