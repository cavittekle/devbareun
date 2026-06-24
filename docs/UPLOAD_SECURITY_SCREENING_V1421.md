# Upload Security Screening and Quarantine Gate — v1.4.21

## Scope

DevBareun now applies deterministic content-security screening **after checksum verification and before any parser library receives the materialized bytes**. This is an admission-control layer for parser safety. It is not an antivirus, malware-detection, sandbox, or external reputation service.

## What is checked

- Declared extension versus magic signature.
- OOXML (`.xlsx`, `.xlsm`) archive validity, entry count, archive traversal paths, total uncompressed size and compression ratio.
- Presence of `vbaProject.bin` in macro-enabled workbooks.
- Selected active PDF markers (`/JavaScript`, `/Launch`, `/RichMedia`, `/EmbeddedFile`) in a bounded sample.

## State model

| `security_scan_status` | `quarantine_status` | Meaning |
|---|---|---|
| `pending` / `scanning` | `pending_scan` | Uploaded source has not completed worker screening. |
| `clean` | `released` | Screening passed; parser may continue. Findings can still be recorded. |
| `blocked` | `quarantined` | Policy or structural check blocked the file. |
| `failed` | `quarantined` | Screening could not safely complete; parser remains blocked. |

When a file is quarantined, its upload status becomes `quarantined`, parser status is `blocked`/`failed`, no result is produced from that execution, and credit consumption remains after-success only.

## Policy flags

```text
DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES=2000
DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES=251658240
DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO=500
DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS=false
DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT=false
```

The last two flags are intentionally opt-in. Macro/active-content detection creates findings by default, but a deployment may elevate those findings to hard blocks after business review. Both Railway services must use the same values.

## Operational response

1. Inspect the upload metadata and `security_scan_error`/`security_scan_findings`.
2. Do not retry unchanged quarantined files. Ask the customer to re-export or re-upload a safe source.
3. Use the staff job recovery flow only after the source is replaced and the file record is no longer quarantined.
4. Keep external malware scanning at the storage/provider perimeter if the customer or regulatory policy requires it.
