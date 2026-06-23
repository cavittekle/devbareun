# Report Snapshot Integrity — v1.4.19

## Purpose

A DevBareun report is an auditable export of a completed analysis. Before this
release, a production report archive row could be retained without its rendered
payload, so a later analysis might affect a subsequent download. v1.4.19 stores
a frozen report snapshot with integrity metadata at generation time.

## Behavior

When `POST /api/reports/generate/{project_id}` succeeds, the `reports` row now
stores:

- `report_payload`: the dashboard payload used to render the export;
- `payload_sha256`: SHA-256 of canonical JSON snapshot content;
- `content_sha256`: SHA-256 of the initially generated PDF/XLSX bytes;
- `snapshot_version`: currently `v1`;
- `generated_at`, `download_count`, and `last_downloaded_at`.

`GET /api/reports/{report_id}/download` prefers an existing local file in
pilot/local mode. Otherwise it renders from the stored `report_payload`, not
from whichever analysis is currently newest. The response has `Cache-Control:
private, no-store` and `X-Content-Type-Options: nosniff`.

## Legacy reports

Reports created before v1.4.19 may not include a snapshot. They remain
downloadable through a compatibility fallback to their archived analysis result,
but API list responses mark them with `snapshot_available: false`. Regenerate
important legacy reports after reviewing the latest analysis to obtain a frozen
snapshot.

## Download audit

After authorization and successful report rendering, the backend calls the
`record_report_download` Supabase RPC. The function increments
`download_count` atomically and is executable only by `service_role`. A
telemetry write failure never prevents a valid, authorized report download.

## Required migration

Run `database/2026_06_19_v1419_report_snapshot_integrity.sql` after v1.4.18.
Then run:

```bash
python tools/check_report_snapshot.py --root .
python tools/check_database_contract.py --root .
```

