# DevBareun v1.4.27 — Production Pilot Acceptance

## Purpose

`tools/pilot_acceptance.py` is the controlled post-deploy verification tool for a real DevBareun environment. It complements the public `smoke_deploy.py` check with an authenticated pilot-account path.

It is designed for a **dedicated pilot customer account**, not an owner, operator, finance or normal customer account. The tool never prints or writes access tokens, cookies, passwords, signed storage URLs, raw request payloads or raw response payloads.

## Safety model

The default mode is read-only:

- public frontend shell;
- backend health, readiness and version;
- CSRF initializer;
- authenticated `/api/auth/me`.

Every state-changing action is deliberately opt-in:

| Operation | Required flags | Potential impact |
|---|---|---|
| Create pilot project and upload fixture | `--write --confirm-write PILOT_WRITE` | Creates a project and small CSV upload record/object. |
| Start analysis | `--run-analysis --confirm-analysis PILOT_ANALYSIS` | Can consume one analysis credit. |
| Generate/download report | `--generate-report --confirm-report PILOT_REPORT` | Creates a frozen report snapshot. |
| Mark project/upload deleted | `--cleanup` | Soft-deletes project and deletes the fixture object where storage permits. |

The tool does not create a payment checkout and must not be used to validate live payment charging. Lemon Squeezy live payment validation remains a separately supervised operator action.

## Authentication

Use one of these methods:

### Recommended: short-lived access token

Provide a short-lived Supabase session token through the process environment. Do not put it in a shell history, source file, `.env` file or CI log.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict \
  --output /secure/path/devbareun-pilot-readonly.json
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

### Alternative: dedicated pilot login

The password is read only from an environment variable. Use a dedicated account with the smallest plan/credit scope required for the pilot.

```bash
export DEVBAREUN_E2E_PASSWORD='<pilot-password>'
python tools/pilot_acceptance.py \
  --frontend-url https://staging.devbareun.com \
  --backend-url https://<railway-staging-backend> \
  --login-email pilot@example.com \
  --strict
unset DEVBAREUN_E2E_PASSWORD
```

## Recommended progression

### 1. Read-only acceptance

Run this immediately after `tools/smoke_deploy.py` succeeds.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

### 2. Controlled upload acceptance

This creates `DevBareun Pilot Acceptance <timestamp>` and uploads a deterministic CSV fixture with a SHA-256 checksum.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict \
  --write --confirm-write PILOT_WRITE \
  --cleanup \
  --output /secure/path/devbareun-pilot-upload.json
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

### 3. Controlled analysis acceptance

Only run after confirming that the pilot account has an intentionally allocated credit. Analysis is not included in the default command because it can consume plan usage.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict \
  --write --confirm-write PILOT_WRITE \
  --run-analysis --confirm-analysis PILOT_ANALYSIS \
  --analysis-timeout 300 \
  --cleanup \
  --output /secure/path/devbareun-pilot-analysis.json
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

### 4. Controlled report acceptance

This requires the analysis mode because a report must be tied to an actual saved analysis result.

```bash
export DEVBAREUN_E2E_ACCESS_TOKEN='<short-lived-pilot-token>'
python tools/pilot_acceptance.py \
  --frontend-url https://devbareun.com \
  --backend-url https://<railway-backend> \
  --strict \
  --write --confirm-write PILOT_WRITE \
  --run-analysis --confirm-analysis PILOT_ANALYSIS \
  --generate-report --confirm-report PILOT_REPORT \
  --analysis-timeout 300 \
  --cleanup
unset DEVBAREUN_E2E_ACCESS_TOKEN
```

## Expected evidence

Optional `--output` creates a **redacted** JSON evidence file containing:

```text
schema version
frontend/backend base URLs without query strings
pass/fail labels
HTTP status codes
public IDs for pilot project/file/job/report
```

It deliberately excludes:

```text
access tokens
passwords
cookies
Authorization headers
CSRF values
signed storage URLs
raw API payloads
customer email
```

Store evidence in the approved operator location rather than committing it to Git or placing it in a public bucket.

## Failure response

1. Do not repeatedly rerun analysis if a worker job fails.
2. Save the redacted evidence output and Railway request/worker logs using the request ID where available.
3. Check **Super Admin → Operations health** for `runtime_not_ready`, worker or archive incidents.
4. Review analysis recovery only after worker health is restored.
5. If upload screening fails, retain the fixture checksum and status; do not bypass checksum or quarantine policy.
6. Do not retry by enabling pilot/local/mock modes in production.

## CI boundary

This tool is intentionally **not executed against a live URL in CI**. CI only runs `tools/check_pilot_acceptance.py`, which verifies the safety contract, documentation links and release integration without requiring provider credentials.
