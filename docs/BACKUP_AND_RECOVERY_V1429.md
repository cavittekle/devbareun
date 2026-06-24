# DevBareun Backup and Disaster Recovery — v1.4.29

## Scope and initial targets

This runbook covers PostgreSQL data, Supabase Storage inventory and recovery
validation. It does not claim that a manifest is a storage backup: an inventory
proves what should exist, while a separate encrypted external copy must retain
actual source/report objects.

Initial operating targets. Confirm these with the business owner before launch:

| Metric | Initial target | Meaning |
|---|---:|---|
| RPO | 24 hours | Maximum acceptable data loss window after a confirmed incident. |
| RTO | 8 hours | Target time to restore a minimum viable service in an isolated recovery environment. |
| Restore drill age | 90 days | Maximum allowed time since the last documented isolated restore drill. |

The policy is represented by these non-secret runtime variables on all Railway
services:

```text
DEVBAREUN_BACKUP_REQUIRED=true
DEVBAREUN_BACKUP_RPO_HOURS=24
DEVBAREUN_BACKUP_RTO_HOURS=8
DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS=90
DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED=true
```

## What must be backed up

1. **PostgreSQL database** — all application tables, including jobs, results,
   credits, reports, audit chain and archive outbox.
2. **Supabase Storage object copies** — `project-files` and `reports` must be
   copied to a separate encrypted backup location by an approved provider or
   operator process.
3. **Storage inventory manifest** — object count and metadata for each private
   bucket; no signed URLs or object content.
4. **Configuration reconstruction record** — deployment runbook, migration
   order, provider env key names and release manifest. Never export live values
   into source control.

## Credential scope

`DEVBAREUN_BACKUP_DATABASE_URL` and any storage service-role key belong only to
a dedicated backup operator or isolated backup runner. They must not be placed
in Vercel or any Railway web/worker service. Use a least-privilege database
backup role if the Supabase plan/connection model permits it.

The committed reference is:

```text
deploy/env/backup-operator.env.template
```

Create an untracked, secured copy outside the repository and validate it first:

```bash
python tools/backup_recovery.py \
  --env-file /secure/path/devbareun-backup.env \
  preflight --require-pg-tools --require-storage
```

The command never prints credentials or database URLs.

## Database backup procedure

1. Ensure the backup target directory is encrypted and outside the repository.
2. Run the guarded command:

```bash
python tools/backup_recovery.py \
  --env-file /secure/path/devbareun-backup.env \
  database-backup \
  --output-dir /secure/encrypted/devbareun-backups \
  --confirm RUN_DATABASE_BACKUP
```

The tool creates:

```text
devbareun-postgres-<timestamp>.dump
devbareun-postgres-<timestamp>.dump.sha256
devbareun-postgres-<timestamp>.dump.metadata.json
```

The dump uses `pg_dump --format=custom`; credentials are passed by libpq
environment variables, not command-line arguments. The metadata records only a
sanitized endpoint and checksum.

Move or replicate the encrypted artifact to a separate retention location. Keep
retention according to legal/customer obligations; this repository does not
impose a retention period.

## Storage inventory and copy verification

Create a metadata-only manifest after the database backup:

```bash
python tools/backup_recovery.py \
  --env-file /secure/path/devbareun-backup.env \
  storage-manifest \
  --output-dir /secure/encrypted/devbareun-backups \
  --buckets project-files,reports \
  --confirm RUN_STORAGE_MANIFEST
```

The manifest is not a substitute for copying objects. Verify that the external
object-copy process has transferred both private buckets, then retain the
manifest beside the copy as an inventory/checkpoint.

## Restore drill procedure

**Do not restore into production.** The supplied utility intentionally has no
production restore command.

1. Create a separate Supabase/PostgreSQL recovery environment with restricted
   access and no production webhook credentials.
2. Select a checksum-verified backup archive and its nearest storage manifest.
3. Validate artifact readability before any restore:

```bash
python tools/backup_recovery.py \
  restore-preflight \
  --dump /secure/encrypted/devbareun-backups/devbareun-postgres-<timestamp>.dump \
  --storage-manifest /secure/encrypted/devbareun-backups/devbareun-storage-manifest-<timestamp>.json \
  --confirm RUN_RESTORE_PREFLIGHT
```

4. In the isolated environment, have an authorized database operator run the
   reviewed `pg_restore` command. Do not point a restore client at the
   production host.
5. Apply only the migration/release version compatible with the dump. Compare
   the release manifest and `database/SUPABASE_DEPLOY_ORDER.md`.
6. Restore object copies to the recovery bucket, compare counts against the
   storage manifest, and run a read-only pilot acceptance test.
7. Record actual restore duration, data cut-off time, object count variance,
   issues and remediation owner. Update the next drill deadline.

## Incident escalation

For a data-loss, corruption or unavailable-database incident:

1. Freeze destructive operations and preserve Railway/Supabase/audit evidence.
2. Open an owner-level incident record with `X-Request-ID`, affected project
   scope and latest verified backup timestamp.
3. Decide whether the RPO/RTO target can be met using the latest verified dump
   and external storage copy.
4. Restore only in the isolated environment first. Validate login, project
   read access, report snapshots, analysis results and object counts.
5. Obtain explicit owner approval before any production cutover.

## Automation limits

`tools/backup_recovery.py` validates and creates database dump / storage
inventory artifacts. It does not schedule backups, copy objects to a third
party, encrypt artifacts, or restore production. Those controls must be
provided by the selected backup destination, scheduler and secure operator
process.
