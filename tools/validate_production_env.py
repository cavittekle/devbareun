#!/usr/bin/env python3
"""Validate DevBareun production environment files before deployment.

The script is intentionally dependency-free so it can run in local shells,
GitHub Actions, Railway build hooks, or any basic Python environment.

Examples:
  python tools/validate_production_env.py --backend-env backend/.env.production --frontend-env frontend/.env.production
  python tools/validate_production_env.py --backend-env backend/.env.example --frontend-env frontend/.env.example --allow-placeholders
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

BACKEND_REQUIRED = [
    "DEVBAREUN_ENV",
    "DEVBAREUN_PRODUCTION_SECURITY",
    "PUBLIC_SITE_URL",
    "DEVBAREUN_ALLOWED_ORIGINS",
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
]

BACKEND_FALSE_FLAGS = [
    "DEVBAREUN_ENABLE_DEV_AUTH",
    "DEVBAREUN_ENABLE_LOCAL_STORE",
    "DEVBAREUN_ENABLE_MOCK_PAYMENT",
    "DEVBAREUN_ENABLE_PILOT_LOGIN",
    "DEVBAREUN_ENABLE_PILOT_CHECKOUT",
    "DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD",
    "DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES",
    "DEVBAREUN_ALLOW_ADMIN_EMAIL_FALLBACK",
    "DEVBAREUN_ALLOW_DEVBAREUN_DOMAIN_ADMINS",
    "DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT",
]

BACKEND_TRUE_FLAGS = [
    "DEVBAREUN_PRODUCTION_SECURITY",
    "DEVBAREUN_REQUIRE_CSRF_TOKEN",
    "DEVBAREUN_RATE_LIMIT_ENABLED",
    "DEVBAREUN_DISABLE_DOCS",
    "DEVBAREUN_REQUIRE_ERROR_TELEMETRY",
    "DEVBAREUN_BACKUP_REQUIRED",
    "DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED",
]

FRONTEND_REQUIRED = [
    "VITE_PUBLIC_SITE_URL",
    "VITE_API_BASE_URL",
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
]

FRONTEND_FORBIDDEN = [
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_JWT_SECRET",
    "LEMON_SQUEEZY_API_KEY",
    "LEMON_SQUEEZY_WEBHOOK_SECRET",
    "UPSTASH_REDIS_REST_TOKEN",
    "DATABASE_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET",
    "DEVBAREUN_SENTRY_DSN",
    "DEVBAREUN_BACKUP_DATABASE_URL",
    "DEVBAREUN_BACKUP_OUTPUT_DIR",
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
    "DEVBAREUN_ERASURE_GRACE_DAYS",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
    "DEVBAREUN_AUTO_PURGE_ENABLED",
    "DEVBAREUN_TEAM_INVITE_TTL_HOURS",
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"^$"),
    re.compile(r"replace", re.I),
    re.compile(r"your-project", re.I),
    re.compile(r"example", re.I),
    re.compile(r"changeme", re.I),
]

TRUE_VALUES = {"1", "true", "yes", "on", "y"}
FALSE_VALUES = {"0", "false", "no", "off", "n"}


def parse_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(str(path))
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def is_placeholder(value: str) -> bool:
    return any(pattern.search(value or "") for pattern in PLACEHOLDER_PATTERNS)


def bool_value(value: str) -> bool | None:
    normalized = (value or "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def split_csv(value: str) -> List[str]:
    return [item.strip().rstrip("/") for item in (value or "").split(",") if item.strip()]


def is_https_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_required(values: Dict[str, str], names: Iterable[str], allow_placeholders: bool, label: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    for name in names:
        if name not in values:
            errors.append(f"{label}: missing {name}")
            continue
        if is_placeholder(values[name]):
            message = f"{label}: {name} is empty or placeholder"
            if allow_placeholders:
                warnings.append(message)
            else:
                errors.append(message)
    return errors, warnings


def validate_backend(values: Dict[str, str], allow_placeholders: bool) -> Tuple[List[str], List[str]]:
    errors, warnings = validate_required(values, BACKEND_REQUIRED, allow_placeholders, "backend")

    env = values.get("DEVBAREUN_ENV", "").lower()
    if env not in {"production", "prod", "live"} and not allow_placeholders:
        errors.append("backend: DEVBAREUN_ENV must be production/prod/live")

    for name in BACKEND_TRUE_FLAGS:
        actual = bool_value(values.get(name, ""))
        if actual is not True:
            errors.append(f"backend: {name} must be true")
    for name in BACKEND_FALSE_FLAGS:
        actual = bool_value(values.get(name, ""))
        if actual is not False:
            errors.append(f"backend: {name} must be false")

    mode = values.get("DEVBAREUN_ANALYSIS_JOB_MODE", "").lower()
    if mode not in {"worker", "background", "inline"}:
        errors.append("backend: DEVBAREUN_ANALYSIS_JOB_MODE must be worker/background/inline")
    elif mode != "worker":
        warnings.append("backend: DEVBAREUN_ANALYSIS_JOB_MODE=worker is recommended for production")

    try:
        max_attempts = int(values.get("DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS", ""))
    except (TypeError, ValueError):
        errors.append("backend: DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS must be an integer between 1 and 10")
    else:
        if not 1 <= max_attempts <= 10:
            errors.append("backend: DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS must be between 1 and 10")

    origins = split_csv(values.get("DEVBAREUN_ALLOWED_ORIGINS") or values.get("CORS_ALLOWED_ORIGINS", ""))
    if not origins:
        errors.append("backend: at least one allowed origin is required")
    for origin in origins:
        if origin == "*":
            errors.append("backend: wildcard origin is not allowed in production")
        elif not is_https_url(origin):
            errors.append(f"backend: origin must be HTTPS: {origin}")

    for name in ("PUBLIC_SITE_URL", "FRONTEND_PUBLIC_API_BASE_URL"):
        value = values.get(name, "")
        if value and not is_https_url(value):
            errors.append(f"backend: {name} must be an HTTPS URL")

    if values.get("DEVBAREUN_PAYMENT_PROVIDER", "").lower() != "lemonsqueezy":
        errors.append("backend: DEVBAREUN_PAYMENT_PROVIDER must be lemonsqueezy")

    try:
        payment_event_attempts = int(values.get("DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS", ""))
    except (TypeError, ValueError):
        errors.append("backend: DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS must be an integer between 1 and 20")
    else:
        if not 1 <= payment_event_attempts <= 20:
            errors.append("backend: DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS must be between 1 and 20")

    try:
        team_invite_ttl = int(values.get("DEVBAREUN_TEAM_INVITE_TTL_HOURS", ""))
    except (TypeError, ValueError):
        errors.append("backend: DEVBAREUN_TEAM_INVITE_TTL_HOURS must be an integer between 1 and 168")
    else:
        if not 1 <= team_invite_ttl <= 168:
            errors.append("backend: DEVBAREUN_TEAM_INVITE_TTL_HOURS must be between 1 and 168")

    archive_mode = values.get("DEVBAREUN_AUDIT_ARCHIVE_MODE", "").strip().lower()
    if archive_mode not in {"disabled", "webhook"}:
        errors.append("backend: DEVBAREUN_AUDIT_ARCHIVE_MODE must be disabled/webhook")
    elif archive_mode != "webhook":
        warnings.append("backend: external audit archive is disabled; v1.4.25 outbox will not leave Supabase")
    archive_url = values.get("DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL", "")
    if archive_mode == "webhook" and archive_url and not is_https_url(archive_url):
        errors.append("backend: DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL must be an HTTPS URL")
    try:
        archive_attempts = int(values.get("DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS", ""))
    except (TypeError, ValueError):
        errors.append("backend: DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS must be an integer between 1 and 20")
    else:
        if not 1 <= archive_attempts <= 20:
            errors.append("backend: DEVBAREUN_AUDIT_ARCHIVE_MAX_ATTEMPTS must be between 1 and 20")

    if values.get("SUPABASE_SERVICE_ROLE_KEY") == values.get("SUPABASE_ANON_KEY") and values.get("SUPABASE_SERVICE_ROLE_KEY"):
        errors.append("backend: SUPABASE_SERVICE_ROLE_KEY must not equal SUPABASE_ANON_KEY")

    telemetry_mode = values.get("DEVBAREUN_ERROR_TELEMETRY_MODE", "").strip().lower()
    if telemetry_mode not in {"log", "sentry", "disabled"}:
        errors.append("backend: DEVBAREUN_ERROR_TELEMETRY_MODE must be log/sentry/disabled")
    elif telemetry_mode != "sentry" and bool_value(values.get("DEVBAREUN_REQUIRE_ERROR_TELEMETRY", "")) is True:
        errors.append("backend: required error telemetry must use DEVBAREUN_ERROR_TELEMETRY_MODE=sentry")
    dsn = values.get("DEVBAREUN_SENTRY_DSN", "")
    if telemetry_mode == "sentry" and dsn and not dsn.startswith("https://"):
        errors.append("backend: DEVBAREUN_SENTRY_DSN must be an HTTPS Sentry DSN")

    for name, minimum, maximum in (
        ("DEVBAREUN_BACKUP_RPO_HOURS", 1, 720),
        ("DEVBAREUN_BACKUP_RTO_HOURS", 1, 168),
        ("DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS", 1, 365),
    ):
        try:
            parsed = int(values.get(name, ""))
        except (TypeError, ValueError):
            errors.append(f"backend: {name} must be an integer between {minimum} and {maximum}")
        else:
            if not minimum <= parsed <= maximum:
                errors.append(f"backend: {name} must be between {minimum} and {maximum}")

    for name, minimum, maximum in (
        ("DEVBAREUN_SOFT_DELETE_RETENTION_DAYS", 7, 365),
        ("DEVBAREUN_ERASURE_GRACE_DAYS", 1, 90),
        ("DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS", 1, 30),
    ):
        try:
            parsed = int(values.get(name, ""))
        except (TypeError, ValueError):
            errors.append(f"backend: {name} must be an integer between {minimum} and {maximum}")
        else:
            if not minimum <= parsed <= maximum:
                errors.append(f"backend: {name} must be between {minimum} and {maximum}")

    auto_purge = bool_value(values.get("DEVBAREUN_AUTO_PURGE_ENABLED", ""))
    if auto_purge is None:
        errors.append("backend: DEVBAREUN_AUTO_PURGE_ENABLED must be true/false")
    elif auto_purge is True:
        warnings.append("backend: automatic purge is enabled; verify a separately reviewed destructive purge operator is deployed.")

    return errors, warnings


def validate_frontend(values: Dict[str, str], allow_placeholders: bool) -> Tuple[List[str], List[str]]:
    errors, warnings = validate_required(values, FRONTEND_REQUIRED, allow_placeholders, "frontend")
    for name in FRONTEND_FORBIDDEN:
        if name in values:
            errors.append(f"frontend: backend-only secret variable must not be present: {name}")
    for name in ("VITE_PUBLIC_SITE_URL", "VITE_API_BASE_URL", "VITE_SUPABASE_URL"):
        value = values.get(name, "")
        if value and not is_https_url(value):
            errors.append(f"frontend: {name} must be an HTTPS URL")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DevBareun production env files.")
    parser.add_argument("--backend-env", type=Path, required=True, help="Path to backend production .env file or exported env file.")
    parser.add_argument("--frontend-env", type=Path, required=True, help="Path to frontend production .env file or exported env file.")
    parser.add_argument("--allow-placeholders", action="store_true", help="Downgrade empty/placeholder values to warnings for checking example files.")
    args = parser.parse_args()

    backend = parse_env(args.backend_env)
    frontend = parse_env(args.frontend_env)

    errors: List[str] = []
    warnings: List[str] = []
    backend_errors, backend_warnings = validate_backend(backend, args.allow_placeholders)
    frontend_errors, frontend_warnings = validate_frontend(frontend, args.allow_placeholders)
    errors.extend(backend_errors)
    errors.extend(frontend_errors)
    warnings.extend(backend_warnings)
    warnings.extend(frontend_warnings)

    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        print(f"Env validation failed: {len(errors)} failure(s), {len(warnings)} warning(s).")
        return 1
    print(f"Env validation passed: {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
