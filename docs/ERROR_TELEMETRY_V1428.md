# DevBareun v1.4.28 — Privacy-Safe Error Telemetry

## Purpose

v1.4.28 adds a unified telemetry boundary for API, analysis-worker and audit-archive-worker errors. The process always emits structured JSON events to Railway logs. Optional Sentry delivery sends only **sanitized synthetic error events**.

## Production configuration

Set the following backend-only values on all Railway services: web, analysis worker and audit archive worker.

```env
DEVBAREUN_ERROR_TELEMETRY_MODE=sentry
DEVBAREUN_REQUIRE_ERROR_TELEMETRY=true
DEVBAREUN_SENTRY_DSN=https://<public-key>@o<org>.ingest.sentry.io/<project>
DEVBAREUN_REQUEST_LOGS_ENABLED=true
```

`DEVBAREUN_SENTRY_DSN` belongs only in Railway. Do not add it to Vercel public environment variables.

## Privacy model

The telemetry module never intentionally sends or emits:

- request body content or uploaded file content;
- cookies, bearer tokens, passwords, API keys, signed URLs or provider secrets;
- raw exception messages to external telemetry.

Every error event includes bounded operational metadata only: service, release, error type, request ID where applicable, HTTP method/path or worker ID. Sentry is initialized with `default_integrations=False`; DevBareun sends a synthetic message such as `api_unhandled_exception:ValueError`, not the raw exception payload.

## Runtime behavior

- `log`: structured Railway logs only.
- `sentry`: structured logs plus sanitized Sentry notifications when the SDK and DSN are available.
- `disabled`: no telemetry integration; use only when `DEVBAREUN_REQUIRE_ERROR_TELEMETRY=false`.

When `DEVBAREUN_REQUIRE_ERROR_TELEMETRY=true`, `/api/readiness` fails if external Sentry telemetry cannot be configured. Owner/operator staff can review the safe state under `/api/operations/health`.

## Verification

```bash
python tools/check_error_telemetry.py --root .
python tools/validate_production_env.py \
  --backend-env /secure/railway-web.env \
  --frontend-env /secure/vercel.env
python tools/check_provider_config.py \
  --railway-web-env /secure/railway-web.env \
  --railway-worker-env /secure/railway-worker.env \
  --railway-audit-archive-env /secure/railway-audit-archive.env \
  --vercel-env /secure/vercel.env
```

After deployment, intentionally exercise a non-destructive bad request and verify the response contains `X-Request-ID`; find the same request ID in Railway structured logs. Do not trigger production server failures solely to test Sentry.

Telemetry events retain the response correlation field as `request_id`; this identifier is safe to share with support and does not contain authentication or customer data.
