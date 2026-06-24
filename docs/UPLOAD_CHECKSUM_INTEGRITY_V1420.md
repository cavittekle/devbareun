# Upload Checksum Integrity — v1.4.20

## Objective

DevBareun analyses construction source files. The analysis must be tied to the exact bytes uploaded by the user, not merely to a mutable storage path or a browser-supplied filename.

## Flow

1. The browser calculates SHA-256 before requesting the signed upload URL.
2. The expected checksum is stored with the upload metadata.
3. The browser cannot replace that expected checksum during `mark-uploaded`.
4. Before parser execution, the worker downloads the private object and recomputes SHA-256 while streaming it to temporary storage.
5. A match becomes `verified`; a mismatch makes the job fail before result creation or credit consumption.

## Operational fields

`uploaded_files` now records `checksum_algorithm`, `checksum_status`, `verified_checksum`, `checksum_verified_at`, and `checksum_error`. Allowed statuses are `not_provided`, `pending_verification`, `verified`, `mismatch`, and `invalid`.

## Production configuration

Set `DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM=true` in Railway web and worker services. It applies to new uploads. Existing historical uploads are not retroactively rejected; they display `not_provided` until re-uploaded.

## Failure behavior

A checksum mismatch fails the analysis job as `runtime_failure`. No analysis result is stored and no credit is consumed. The source file record retains its mismatch status for staff investigation.
