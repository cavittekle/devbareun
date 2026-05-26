# DevBareun Backend Connection

Frontend connects to the backend through `js/api-client.js`.

## Current production backend

```text
https://devbareun-backend-production.up.railway.app
```

After deploying a new backend package, verify the active Railway version here:

```text
https://devbareun-backend-production.up.railway.app/health
```

Expected backend version for this package:

```text
1.1.3-fixed-release
```

## Local behavior

When the frontend is opened from `localhost`, `127.0.0.1` or `file://`, `js/api-client.js` still uses the Railway backend by default unless `localStorage.devbareun_api_base` is manually set. This avoids accidental `localhost:8000` fetch errors on static previews.

## Connected flow

1. User selects analysis type.
2. User uploads project files.
3. Frontend creates project with `POST /api/projects`.
4. Frontend uploads files with `POST /api/projects/{project_id}/upload`.
5. Frontend calls preflight with `POST /api/projects/{project_id}/preflight`.
6. User reviews detected mappings and missing fields.
7. Unlock/payment step calls `POST /api/payments/create-checkout`.
8. In pilot mode the backend unlocks the result immediately.
9. If Stripe is configured, the backend returns `checkout_url` and the frontend redirects to Stripe Checkout.
10. Frontend calls analysis with `POST /api/projects/{project_id}/analyze` after unlock.
11. Result page reads backend JSON and updates dashboard/PDF/Excel export links.

## Important design principle

The backend does not assume that every customer Excel file has the same template. It first classifies sheets, maps columns and calculates dashboard values only where the data is confidently detected. Missing or unclear data is shown for confirmation instead of using fake sample values.
