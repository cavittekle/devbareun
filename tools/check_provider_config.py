#!/usr/bin/env python3
"""Check that Railway web/worker and Vercel production configuration agree.

The checker deliberately reads only local exported env files. It never contacts
providers and never prints values, so it can be used before a deployment or in
CI against the committed placeholder templates.

Examples:
  python tools/check_provider_config.py \
    --railway-web-env /secure/railway-web.env \
    --railway-worker-env /secure/railway-worker.env \
    --vercel-env /secure/vercel.env

  python tools/check_provider_config.py \
    --railway-web-env deploy/env/railway-web.env.template \
    --railway-worker-env deploy/env/railway-worker.env.template \
    --vercel-env deploy/env/vercel.env.template \
    --allow-placeholders
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from validate_production_env import (
    FRONTEND_FORBIDDEN,
    bool_value,
    parse_env,
    validate_backend,
    validate_frontend,
)

# These values affect shared data access, security, API behaviour and payment
# processing. A worker that differs from the web service can create hard-to-
# diagnose processing failures, therefore every listed key must be identical.
RAILWAY_SHARED_KEYS = (
    "DEVBAREUN_ENV",
    "APP_ENV",
    "DEVBAREUN_PRODUCTION_SECURITY",
    "DEVBAREUN_REQUIRE_CSRF_TOKEN",
    "DEVBAREUN_ANALYSIS_JOB_MODE",
    "DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS",
    "DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM",
    "DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES",
    "DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES",
    "DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO",
    "DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS",
    "DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT",
    "DEVBAREUN_AUDIT_ARCHIVE_MODE",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET",
    "DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS",
    "DEVBAREUN_AUDIT_ARCHIVE_BATCH_SIZE",
    "DEVBAREUN_AUDIT_ARCHIVE_LEASE_SECONDS",
    "DEVBAREUN_AUDIT_ARCHIVE_TIMEOUT_SECONDS",
    "DEVBAREUN_AUDIT_ARCHIVE_WORKER_STATUS_STALE_SECONDS",
    "DEVBAREUN_ERROR_TELEMETRY_MODE",
    "DEVBAREUN_REQUIRE_ERROR_TELEMETRY",
    "DEVBAREUN_SENTRY_DSN",
    "DEVBAREUN_REQUEST_LOGS_ENABLED",
    "DEVBAREUN_BACKUP_REQUIRED",
    "DEVBAREUN_BACKUP_RPO_HOURS",
    "DEVBAREUN_BACKUP_RTO_HOURS",
    "DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS",
    "DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED",
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
    "DEVBAREUN_ERASURE_GRACE_DAYS",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
    "DEVBAREUN_AUTO_PURGE_ENABLED",
    "DEVBAREUN_TEAM_INVITE_TTL_HOURS",
    "PUBLIC_SITE_URL",
    "DEVBAREUN_ALLOWED_ORIGINS",
    "CORS_ALLOWED_ORIGINS",
    "DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS",
    "FRONTEND_PUBLIC_API_BASE_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "SUPABASE_REPORTS_BUCKET",
    "DEVBAREUN_PAYMENT_PROVIDER",
    "LEMON_SQUEEZY_API_KEY",
    "LEMON_SQUEEZY_STORE_ID",
    "LEMON_SQUEEZY_WEBHOOK_SECRET",
    "LEMON_SQUEEZY_SINGLE_VARIANT_ID",
    "LEMON_SQUEEZY_PLUS_VARIANT_ID",
    "LEMON_SQUEEZY_PRO_VARIANT_ID",
    "DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
)

# Browser-visible values must agree with their backend equivalents. The list
# intentionally contains only public values; it never compares backend secrets
# against frontend configuration.
PUBLIC_ALIGNMENT = (
    ("PUBLIC_SITE_URL", "VITE_PUBLIC_SITE_URL"),
    ("FRONTEND_PUBLIC_API_BASE_URL", "VITE_API_BASE_URL"),
    ("FRONTEND_PUBLIC_API_BASE_URL", "VITE_API_URL"),
    ("FRONTEND_PUBLIC_API_BASE_URL", "VITE_DEVBAREUN_API_BASE_URL"),
    ("SUPABASE_URL", "VITE_SUPABASE_URL"),
    ("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"),
)


@dataclass
class ProviderConfigResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_files: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def add_validation_messages(
    result: ProviderConfigResult,
    label: str,
    messages: Iterable[str],
    level: str,
) -> None:
    for message in messages:
        text = f"{label}: {message}"
        if level == "error":
            result.add_error(text)
        else:
            result.add_warning(text)


def compare_same(
    result: ProviderConfigResult,
    left: Dict[str, str],
    right: Dict[str, str],
    keys: Iterable[str],
    left_label: str,
    right_label: str,
) -> None:
    for key in keys:
        if key not in left:
            result.add_error(f"{left_label}: missing shared key {key}")
            continue
        if key not in right:
            result.add_error(f"{right_label}: missing shared key {key}")
            continue
        if left[key] != right[key]:
            result.add_error(f"configuration drift: {key} differs between {left_label} and {right_label}")


def compare_public_alignment(
    result: ProviderConfigResult,
    backend: Dict[str, str],
    frontend: Dict[str, str],
) -> None:
    for backend_key, frontend_key in PUBLIC_ALIGNMENT:
        if backend_key not in backend:
            result.add_error(f"railway web: missing public alignment key {backend_key}")
            continue
        if frontend_key not in frontend:
            result.add_error(f"vercel: missing public alignment key {frontend_key}")
            continue
        if backend[backend_key] != frontend[frontend_key]:
            result.add_error(f"public configuration drift: {backend_key} does not match {frontend_key}")


def validate_worker_mode(result: ProviderConfigResult, worker: Dict[str, str]) -> None:
    if worker.get("DEVBAREUN_ANALYSIS_JOB_MODE", "").strip().lower() != "worker":
        result.add_error("railway worker: DEVBAREUN_ANALYSIS_JOB_MODE must be worker")
    if bool_value(worker.get("DEVBAREUN_PRODUCTION_SECURITY", "")) is not True:
        result.add_error("railway worker: DEVBAREUN_PRODUCTION_SECURITY must be true")


def check_provider_config(
    railway_web: Dict[str, str],
    railway_worker: Dict[str, str],
    vercel: Dict[str, str],
    *,
    railway_audit_archive: Dict[str, str] | None = None,
    allow_placeholders: bool = False,
) -> ProviderConfigResult:
    result = ProviderConfigResult()

    web_errors, web_warnings = validate_backend(railway_web, allow_placeholders)
    worker_errors, worker_warnings = validate_backend(railway_worker, allow_placeholders)
    vercel_errors, vercel_warnings = validate_frontend(vercel, allow_placeholders)
    add_validation_messages(result, "railway web", web_errors, "error")
    add_validation_messages(result, "railway worker", worker_errors, "error")
    add_validation_messages(result, "vercel", vercel_errors, "error")
    add_validation_messages(result, "railway web", web_warnings, "warning")
    add_validation_messages(result, "railway worker", worker_warnings, "warning")
    add_validation_messages(result, "vercel", vercel_warnings, "warning")

    compare_same(result, railway_web, railway_worker, RAILWAY_SHARED_KEYS, "railway web", "railway worker")
    if railway_audit_archive is not None:
        archive_errors, archive_warnings = validate_backend(railway_audit_archive, allow_placeholders)
        add_validation_messages(result, "railway audit archive", archive_errors, "error")
        add_validation_messages(result, "railway audit archive", archive_warnings, "warning")
        compare_same(result, railway_web, railway_audit_archive, RAILWAY_SHARED_KEYS, "railway web", "railway audit archive")
        if railway_audit_archive.get("DEVBAREUN_AUDIT_ARCHIVE_MODE", "").strip().lower() != "webhook":
            result.add_error("railway audit archive: DEVBAREUN_AUDIT_ARCHIVE_MODE must be webhook")
    compare_public_alignment(result, railway_web, vercel)
    validate_worker_mode(result, railway_worker)

    for secret in FRONTEND_FORBIDDEN:
        if secret in vercel:
            result.add_error(f"vercel: forbidden backend-only key present: {secret}")

    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun Railway/Vercel configuration alignment.")
    parser.add_argument("--railway-web-env", type=Path, required=True, help="Exported Railway web environment file.")
    parser.add_argument("--railway-worker-env", type=Path, required=True, help="Exported Railway worker environment file.")
    parser.add_argument("--vercel-env", type=Path, required=True, help="Exported Vercel environment file.")
    parser.add_argument("--railway-audit-archive-env", type=Path, default=None, help="Optional exported Railway audit archive worker environment file.")
    parser.add_argument("--allow-placeholders", action="store_true", help="Permit placeholder values for committed templates only.")
    parser.add_argument("--json", action="store_true", help="Print only status metadata; secret values are never emitted.")
    args = parser.parse_args(argv)

    try:
        web = parse_env(args.railway_web_env)
        worker = parse_env(args.railway_worker_env)
        vercel = parse_env(args.vercel_env)
        audit_archive = parse_env(args.railway_audit_archive_env) if args.railway_audit_archive_env else None
    except FileNotFoundError as exc:
        print(f"[FAIL] env file not found: {exc}")
        return 2

    result = check_provider_config(web, worker, vercel, railway_audit_archive=audit_archive, allow_placeholders=args.allow_placeholders)
    result.checked_files = [
        str(args.railway_web_env),
        str(args.railway_worker_env),
        str(args.vercel_env),
    ] + ([str(args.railway_audit_archive_env)] if args.railway_audit_archive_env else [])

    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings, "checked_files": result.checked_files}, indent=2))
    else:
        for warning in result.warnings:
            print(f"[WARN] {warning}")
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Provider configuration check {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
