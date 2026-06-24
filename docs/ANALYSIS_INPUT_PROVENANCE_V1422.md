# Analysis Input Provenance — v1.4.22

Every analysis job now records an immutable, privacy-safe snapshot of the files that were selected and actually admitted to the parser. The snapshot is stored on both `analysis_jobs` and the completed `analysis_results` row.

## What the snapshot contains

- Source file id, displayed filename, extension and size.
- Declared or worker-verified SHA-256 content hash status.
- Checksum verification time/status.
- Deterministic upload security-screening and quarantine statuses.
- Parser status, snapshot schema version and the analysis-engine version.
- A deterministic `source_fingerprint` calculated from the sorted source records.

The same verified file set produces the same fingerprint across retries. `captured_at` and the app version are not part of the fingerprint calculation.

## What it deliberately excludes

The snapshot never stores Supabase storage paths, signed URLs, user identifiers, access tokens, provider secrets or the raw uploaded file content. A SHA-256 hash is an integrity identifier; it does not permit a caller to access storage.

## Operational meaning

- A job gets an initial snapshot before parsing, so a checksum/security rejection is still auditable.
- After materialization, checksum verification and screening, the snapshot is refreshed and persisted with the completed result.
- A report generated from that result retains the same provenance inside its frozen report payload.
- The workspace result screen exposes a concise source-traceability panel for authorized project users.

This is an auditability feature, not a security scanner and not a legal document-management retention policy. Existing results created before v1.4.22 may display no provenance snapshot.

## Deployment

1. Apply `database/2026_06_19_v1422_analysis_input_provenance.sql` after v1.4.21.
2. Deploy Railway web and worker services from the same release.
3. Run one analysis with a supported upload and verify `input_manifest`, `input_manifest_sha256` and `input_file_count` on the resulting analysis row.
4. Confirm the workspace result shows **Analysis source traceability** and no storage URL is returned.

Static contract check:

```bash
python tools/check_analysis_provenance.py --root .
```
