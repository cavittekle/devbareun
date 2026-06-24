#!/usr/bin/env python3
"""DevBareun backup and disaster-recovery operator utility.

The utility intentionally avoids provider-side writes and never restores a
production database. It supports three bounded operator actions:

* ``preflight`` validates policy and local tooling without printing secrets.
* ``database-backup`` creates a PostgreSQL custom-format dump using libpq
  environment variables so credentials never appear in process arguments.
* ``storage-manifest`` inventories private Supabase Storage buckets without
  downloading customer files or emitting signed URLs.
* ``restore-preflight`` verifies a database dump and an optional storage
  manifest before a restoration drill in an isolated environment.

Actual restores must be performed only into an isolated recovery project or
staging database under the documented runbook. This command deliberately has
no ``restore`` action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

DEFAULT_BUCKETS = ("project-files", "reports")
PLACEHOLDER_TOKENS = ("replace", "example", "your-", "changeme", "<")


@dataclass(frozen=True)
class BackupPolicy:
    required: bool
    rpo_hours: int
    rto_hours: int
    drill_max_age_days: int
    storage_manifest_required: bool


def _bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _int(value: str | None, *, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def load_env(path: Path | None) -> dict[str, str]:
    """Read a simple .env/export file without modifying the current process."""
    if path is None:
        return dict(os.environ)
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def policy_from_env(values: Mapping[str, str]) -> BackupPolicy:
    return BackupPolicy(
        required=_bool(values.get("DEVBAREUN_BACKUP_REQUIRED"), default=True),
        rpo_hours=_int(values.get("DEVBAREUN_BACKUP_RPO_HOURS", "24"), name="DEVBAREUN_BACKUP_RPO_HOURS", minimum=1, maximum=720),
        rto_hours=_int(values.get("DEVBAREUN_BACKUP_RTO_HOURS", "8"), name="DEVBAREUN_BACKUP_RTO_HOURS", minimum=1, maximum=168),
        drill_max_age_days=_int(values.get("DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS", "90"), name="DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS", minimum=1, maximum=365),
        storage_manifest_required=_bool(values.get("DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED"), default=True),
    )


def is_placeholder(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return not normalized or any(token in normalized for token in PLACEHOLDER_TOKENS)


def sanitize_database_url(database_url: str) -> str:
    """Return only safe endpoint metadata; strip user, password, query and path credentials."""
    parsed = urlparse(database_url)
    host = parsed.hostname or "unknown-host"
    database = (parsed.path or "/").lstrip("/") or "unknown-db"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme or 'postgresql'}://{host}{port}/{database}"


def database_env_from_url(database_url: str) -> dict[str, str]:
    """Convert a PostgreSQL URL to libpq env vars for a child pg_dump process.

    Password remains in the child environment and is never included in command
    arguments or output.
    """
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DEVBAREUN_BACKUP_DATABASE_URL must use postgres:// or postgresql://")
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise ValueError("DEVBAREUN_BACKUP_DATABASE_URL must include host and database name")
    result = {
        "PGHOST": parsed.hostname,
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": unquote(parsed.username or ""),
        "PGDATABASE": unquote(parsed.path.lstrip("/")),
    }
    if parsed.password is not None:
        result["PGPASSWORD"] = unquote(parsed.password)
    if not result["PGUSER"]:
        raise ValueError("DEVBAREUN_BACKUP_DATABASE_URL must include database user")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    cwd = Path.cwd().resolve()
    if resolved == cwd or cwd in resolved.parents or resolved in cwd.parents:
        raise ValueError("backup output directory must not be inside or above the repository root; choose an external encrypted backup location")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def preflight(values: Mapping[str, str], *, require_pg_tools: bool, require_storage: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        policy = policy_from_env(values)
    except ValueError as exc:
        return [str(exc)], warnings
    if not policy.required:
        errors.append("DEVBAREUN_BACKUP_REQUIRED must be true for production policy")
    if require_pg_tools and not command_exists("pg_dump"):
        errors.append("pg_dump is not installed or not in PATH")
    if require_pg_tools and not command_exists("pg_restore"):
        errors.append("pg_restore is not installed or not in PATH")
    database_url = values.get("DEVBAREUN_BACKUP_DATABASE_URL", "")
    if require_pg_tools and is_placeholder(database_url):
        errors.append("DEVBAREUN_BACKUP_DATABASE_URL is required for database backup operations")
    elif database_url:
        try:
            database_env_from_url(database_url)
        except ValueError as exc:
            errors.append(str(exc))
    if require_storage:
        for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
            if is_placeholder(values.get(key)):
                errors.append(f"{key} is required for storage inventory operations")
    if policy.rpo_hours > 24:
        warnings.append("RPO exceeds 24 hours; confirm this is acceptable for paid project data")
    if policy.drill_max_age_days > 90:
        warnings.append("restore drill interval exceeds 90 days")
    return errors, warnings


def require_confirmation(actual: str | None, expected: str, action: str) -> None:
    if actual != expected:
        raise ValueError(f"{action} requires --confirm {expected}")


def run_database_backup(values: Mapping[str, str], output_dir: Path, confirmation: str | None) -> Path:
    require_confirmation(confirmation, "RUN_DATABASE_BACKUP", "database backup")
    errors, warnings = preflight(values, require_pg_tools=True, require_storage=False)
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        raise ValueError("; ".join(errors))

    directory = safe_output_dir(output_dir)
    database_url = values["DEVBAREUN_BACKUP_DATABASE_URL"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = directory / f"devbareun-postgres-{timestamp}.dump"
    child_env = os.environ.copy()
    child_env.update(database_env_from_url(database_url))
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(archive),
    ]
    result = subprocess.run(command, env=child_env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        archive.unlink(missing_ok=True)
        raise RuntimeError("pg_dump failed; inspect secure operator logs without printing credentials")
    digest = sha256_file(archive)
    archive.with_suffix(archive.suffix + ".sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    metadata = {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "artifact": archive.name,
        "artifact_sha256": digest,
        "artifact_bytes": archive.stat().st_size,
        "database_endpoint": sanitize_database_url(database_url),
        "format": "pg_dump_custom",
        "restore_target_policy": "isolated_environment_only",
    }
    write_json(archive.with_suffix(archive.suffix + ".metadata.json"), metadata)
    print(f"Created database backup: {archive.name}")
    print(f"SHA-256: {digest}")
    return archive


def _storage_request(url: str, service_role_key: str, payload: Mapping[str, Any]) -> Any:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - operator-supplied HTTPS endpoint
        return json.loads(response.read().decode("utf-8"))


def _sanitize_storage_entries(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for entry in entries:
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), Mapping) else {}
        safe.append({
            "name": str(entry.get("name") or ""),
            "id": str(entry.get("id") or ""),
            "updated_at": entry.get("updated_at"),
            "created_at": entry.get("created_at"),
            "last_accessed_at": entry.get("last_accessed_at"),
            "size": metadata.get("size"),
            "mimetype": metadata.get("mimetype"),
            "etag": metadata.get("eTag") or metadata.get("etag"),
        })
    return safe


def run_storage_manifest(values: Mapping[str, str], output_dir: Path, buckets: Sequence[str], confirmation: str | None) -> Path:
    require_confirmation(confirmation, "RUN_STORAGE_MANIFEST", "storage manifest")
    errors, warnings = preflight(values, require_pg_tools=False, require_storage=True)
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        raise ValueError("; ".join(errors))
    directory = safe_output_dir(output_dir)
    base = values["SUPABASE_URL"].rstrip("/")
    key = values["SUPABASE_SERVICE_ROLE_KEY"]
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "inventory_only": True,
        "signed_urls_included": False,
        "buckets": {},
    }
    for bucket in buckets:
        bucket = bucket.strip()
        if not bucket:
            continue
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = _storage_request(
                f"{base}/storage/v1/object/list/{bucket}",
                key,
                {"prefix": "", "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}},
            )
            if not isinstance(page, list):
                raise RuntimeError(f"unexpected storage list response for bucket {bucket}")
            entries = _sanitize_storage_entries([item for item in page if isinstance(item, Mapping)])
            items.extend(entries)
            if len(page) < 1000:
                break
            offset += len(page)
            time.sleep(0.1)
        manifest["buckets"][bucket] = {"object_count": len(items), "objects": items}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    destination = directory / f"devbareun-storage-manifest-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_json(destination, manifest)
    print(f"Created storage inventory manifest: {destination.name}")
    return destination


def verify_checksum(dump: Path) -> tuple[bool, str]:
    sidecar = dump.with_suffix(dump.suffix + ".sha256")
    if not sidecar.exists():
        return False, "checksum sidecar is missing"
    expected = sidecar.read_text(encoding="utf-8").strip().split()[0] if sidecar.read_text(encoding="utf-8").strip() else ""
    actual = sha256_file(dump)
    if not expected:
        return False, "checksum sidecar is empty"
    return expected == actual, "checksum verified" if expected == actual else "checksum mismatch"


def run_restore_preflight(dump: Path, storage_manifest: Path | None, confirmation: str | None) -> dict[str, Any]:
    require_confirmation(confirmation, "RUN_RESTORE_PREFLIGHT", "restore preflight")
    if not dump.exists() or not dump.is_file():
        raise ValueError("database dump file does not exist")
    if not command_exists("pg_restore"):
        raise ValueError("pg_restore is not installed or not in PATH")
    checksum_ok, checksum_message = verify_checksum(dump)
    if not checksum_ok:
        raise ValueError(checksum_message)
    result = subprocess.run(["pg_restore", "--list", str(dump)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("pg_restore could not read the dump archive")
    manifest_summary: dict[str, Any] | None = None
    if storage_manifest is not None:
        payload = json.loads(storage_manifest.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or payload.get("schema_version") != 1 or not isinstance(payload.get("buckets"), Mapping):
            raise ValueError("storage manifest does not match the expected schema")
        manifest_summary = {
            "file": storage_manifest.name,
            "bucket_count": len(payload["buckets"]),
            "object_count": sum(int(info.get("object_count", 0)) for info in payload["buckets"].values() if isinstance(info, Mapping)),
        }
    report = {
        "checked_at_utc": now_utc(),
        "dump": dump.name,
        "dump_sha256": sha256_file(dump),
        "pg_restore_readable": True,
        "restore_target_policy": "isolated_environment_only",
        "storage_manifest": manifest_summary,
    }
    print(json.dumps(report, indent=2))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DevBareun backup and disaster-recovery operator utility.")
    parser.add_argument("--env-file", type=Path, help="Secure operator env file. Defaults to current environment.")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight_cmd = sub.add_parser("preflight", help="Validate backup policy/tooling without running a backup.")
    preflight_cmd.add_argument("--require-pg-tools", action="store_true")
    preflight_cmd.add_argument("--require-storage", action="store_true")

    db_cmd = sub.add_parser("database-backup", help="Create a pg_dump custom archive; never runs restore.")
    db_cmd.add_argument("--output-dir", type=Path, help="Encrypted output directory. Defaults to DEVBAREUN_BACKUP_OUTPUT_DIR.")
    db_cmd.add_argument("--confirm")

    storage_cmd = sub.add_parser("storage-manifest", help="Create a private Storage inventory manifest; does not copy files.")
    storage_cmd.add_argument("--output-dir", type=Path, help="Encrypted output directory. Defaults to DEVBAREUN_BACKUP_OUTPUT_DIR.")
    storage_cmd.add_argument("--buckets", default=",".join(DEFAULT_BUCKETS))
    storage_cmd.add_argument("--confirm")

    restore_cmd = sub.add_parser("restore-preflight", help="Verify a backup archive before an isolated restore drill.")
    restore_cmd.add_argument("--dump", type=Path, required=True)
    restore_cmd.add_argument("--storage-manifest", type=Path)
    restore_cmd.add_argument("--confirm")

    args = parser.parse_args(argv)
    try:
        values = load_env(args.env_file)
        if args.command == "preflight":
            errors, warnings = preflight(values, require_pg_tools=args.require_pg_tools, require_storage=args.require_storage)
            for warning in warnings:
                print(f"[WARN] {warning}")
            for error in errors:
                print(f"[FAIL] {error}")
            print(f"Backup preflight {'passed' if not errors else 'failed'}: {len(errors)} error(s).")
            return 0 if not errors else 1
        if args.command == "database-backup":
            output_raw = str(args.output_dir) if args.output_dir is not None else values.get("DEVBAREUN_BACKUP_OUTPUT_DIR", "")
            if not output_raw:
                raise ValueError("--output-dir or DEVBAREUN_BACKUP_OUTPUT_DIR is required")
            run_database_backup(values, Path(output_raw), args.confirm)
            return 0
        if args.command == "storage-manifest":
            output_raw = str(args.output_dir) if args.output_dir is not None else values.get("DEVBAREUN_BACKUP_OUTPUT_DIR", "")
            if not output_raw:
                raise ValueError("--output-dir or DEVBAREUN_BACKUP_OUTPUT_DIR is required")
            buckets = [item.strip() for item in args.buckets.split(",") if item.strip()]
            run_storage_manifest(values, Path(output_raw), buckets, args.confirm)
            return 0
        if args.command == "restore-preflight":
            run_restore_preflight(args.dump, args.storage_manifest, args.confirm)
            return 0
        return 2
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
