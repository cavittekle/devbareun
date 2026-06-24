#!/usr/bin/env python3
"""Validate DevBareun production deployment runbook coverage.

This check intentionally stays dependency-free. It does not contact providers;
it verifies that the repository contains a complete, operator-readable runbook
for the exact deployment surface that the code expects: Supabase migrations and
storage, Railway web + worker services, Vercel frontend, Lemon Squeezy webhook,
production env validation, smoke tests and rollback steps.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

RUNBOOK_PATH = Path("docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md")
ENV_MATRIX_PATH = Path("docs/DEPLOYMENT_ENV_MATRIX_V1414.md")
CONFIG_PREFLIGHT_PATH = Path("docs/PRODUCTION_CONFIG_PREFLIGHT_V1415.md")
PROVIDER_TEMPLATE_PATHS = (
    Path("deploy/env/railway-web.env.template"),
    Path("deploy/env/railway-worker.env.template"),
    Path("deploy/env/railway-audit-archive.env.template"),
    Path("deploy/env/vercel.env.template"),
)
DEPLOY_ORDER_PATH = Path("database/SUPABASE_DEPLOY_ORDER.md")
BACKUP_OPERATOR_TEMPLATE_PATH = Path("deploy/env/backup-operator.env.template")

REQUIRED_RUNBOOK_PHRASES = [
    "Supabase",
    "Railway web service",
    "Railway worker service",
    "Railway audit archive worker",
    "Vercel",
    "Lemon Squeezy",
    "rollback",
    "smoke test",
    "Root Directory = backend",
    "Root Directory = frontend",
    "project-files",
    "reports",
    "DEVBAREUN_ENV=production",
    "DEVBAREUN_PRODUCTION_SECURITY=true",
    "DEVBAREUN_REQUIRE_CSRF_TOKEN=true",
    "DEVBAREUN_ANALYSIS_JOB_MODE=worker",
    "python tools/validate_production_env.py",
    "python tools/check_database_contract.py",
    "python tools/check_deploy_runbook.py",
    "python tools/check_provider_config.py",
    "deploy/env/railway-web.env.template",
    "deploy/env/railway-worker.env.template",
    "deploy/env/railway-audit-archive.env.template",
    "deploy/env/vercel.env.template",
    "python tools/smoke_deploy.py",
    "python -m app.analysis_worker --loop",
    "python -m app.audit_archive_worker --loop",
    "DEVBAREUN_AUDIT_ARCHIVE_MODE=webhook",
    "npm ci",
    "npm run build",
    "python tools/pilot_acceptance.py",
    "DEVBAREUN_ERROR_TELEMETRY_MODE=sentry",
    "DEVBAREUN_REQUIRE_ERROR_TELEMETRY=true",
    "DEVBAREUN_SENTRY_DSN",
    "python tools/check_error_telemetry.py",
    "DEVBAREUN_BACKUP_REQUIRED=true",
    "DEVBAREUN_BACKUP_RPO_HOURS=24",
    "DEVBAREUN_BACKUP_RTO_HOURS=8",
    "deploy/env/backup-operator.env.template",
    "docs/BACKUP_AND_RECOVERY_V1429.md",
    "python tools/check_data_lifecycle.py",
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS=30",
    "DEVBAREUN_ERASURE_GRACE_DAYS=14",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS=7",
    "DEVBAREUN_AUTO_PURGE_ENABLED=false",
    "DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS=5",
    "GET /api/billing/checkouts/{checkout_id}",
    "DEVBAREUN_TEAM_INVITE_TTL_HOURS=72",
    "python tools/check_company_team_foundation.py",
    "python tools/check_project_sharing.py",
]

REQUIRED_ENV_MATRIX_KEYS = [
    "DEVBAREUN_ENV",
    "DEVBAREUN_PRODUCTION_SECURITY",
    "DEVBAREUN_REQUIRE_CSRF_TOKEN",
    "DEVBAREUN_ANALYSIS_JOB_MODE",
    "DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM",
    "DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES",
    "DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES",
    "DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO",
    "DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS",
    "DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT",
    "DEVBAREUN_AUDIT_ARCHIVE_MODE",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET",
    "DEVBAREUN_ERROR_TELEMETRY_MODE",
    "DEVBAREUN_REQUIRE_ERROR_TELEMETRY",
    "DEVBAREUN_SENTRY_DSN",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "SUPABASE_REPORTS_BUCKET",
    "LEMON_SQUEEZY_API_KEY",
    "LEMON_SQUEEZY_WEBHOOK_SECRET",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "VITE_API_BASE_URL",
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "DEVBAREUN_BACKUP_REQUIRED",
    "DEVBAREUN_BACKUP_RPO_HOURS",
    "DEVBAREUN_BACKUP_RTO_HOURS",
    "DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS",
    "DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED",
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
    "DEVBAREUN_ERASURE_GRACE_DAYS",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
    "DEVBAREUN_AUTO_PURGE_ENABLED",
    "DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS",
    "DEVBAREUN_TEAM_INVITE_TTL_HOURS",
]

FRONTEND_FORBIDDEN_SECRETS = [
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_JWT_SECRET",
    "LEMON_SQUEEZY_API_KEY",
    "LEMON_SQUEEZY_WEBHOOK_SECRET",
    "UPSTASH_REDIS_REST_TOKEN",
    "DATABASE_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL",
    "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET",
    "DEVBAREUN_ERROR_TELEMETRY_MODE",
    "DEVBAREUN_REQUIRE_ERROR_TELEMETRY",
    "DEVBAREUN_SENTRY_DSN",
    "DEVBAREUN_BACKUP_DATABASE_URL",
    "DEVBAREUN_BACKUP_OUTPUT_DIR",
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
    "DEVBAREUN_ERASURE_GRACE_DAYS",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
    "DEVBAREUN_AUTO_PURGE_ENABLED",
    "DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS",
    "DEVBAREUN_TEAM_INVITE_TTL_HOURS",
]

DEPLOY_ORDER_RE = re.compile(r"`([^`]+\.sql)`")


@dataclass
class RunbookResult:
    errors: List[str]
    warnings: List[str]
    deploy_order: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_deploy_order(root: Path, result: RunbookResult) -> List[str]:
    path = root / DEPLOY_ORDER_PATH
    if not path.exists():
        result.add_error(f"missing deploy order: {DEPLOY_ORDER_PATH.as_posix()}")
        return []
    items = DEPLOY_ORDER_RE.findall(read_text(path))
    if not items:
        result.add_error("database/SUPABASE_DEPLOY_ORDER.md does not list SQL migration files")
    for item in items:
        if not (root / "database" / item).exists():
            result.add_error(f"deploy-order SQL file is missing: database/{item}")
    return items


def check_runbook(root: Path, result: RunbookResult, deploy_order: List[str]) -> None:
    path = root / RUNBOOK_PATH
    if not path.exists():
        result.add_error(f"missing runbook: {RUNBOOK_PATH.as_posix()}")
        return
    text = read_text(path)
    lowered = text.lower()
    for phrase in REQUIRED_RUNBOOK_PHRASES:
        if phrase.lower() not in lowered:
            result.add_error(f"runbook missing required phrase/command: {phrase}")
    for migration in deploy_order:
        if migration not in text:
            result.add_error(f"runbook does not mention deploy-order migration: {migration}")
    if "do not place" not in lowered or "frontend" not in lowered or "service role" not in lowered:
        result.add_error("runbook must explicitly prohibit frontend service-role secrets")
    if text.count("```bash") < 4:
        result.add_warning("runbook has fewer bash command blocks than expected")


def check_env_matrix(root: Path, result: RunbookResult) -> None:
    path = root / ENV_MATRIX_PATH
    if not path.exists():
        result.add_error(f"missing env matrix: {ENV_MATRIX_PATH.as_posix()}")
        return
    text = read_text(path)
    for key in REQUIRED_ENV_MATRIX_KEYS:
        if key not in text:
            result.add_error(f"env matrix missing key: {key}")
    for secret in FRONTEND_FORBIDDEN_SECRETS:
        marker = f"{secret} | Backend only"
        if marker not in text and f"`{secret}` | Backend only" not in text:
            result.add_error(f"env matrix must mark {secret} as Backend only")
    if "Vercel" not in text or "Railway" not in text or "Supabase" not in text:
        result.add_error("env matrix must identify Vercel, Railway and Supabase scopes")


def check_config_preflight(root: Path, result: RunbookResult) -> None:
    path = root / CONFIG_PREFLIGHT_PATH
    if not path.exists():
        result.add_error(f"missing production config preflight: {CONFIG_PREFLIGHT_PATH.as_posix()}")
    else:
        text = read_text(path)
        for phrase in (
            "tools/check_provider_config.py",
            "railway web",
            "railway worker",
            "vercel",
            "configuration drift",
            "SUPABASE_SERVICE_ROLE_KEY",
        ):
            if phrase.lower() not in text.lower():
                result.add_error(f"production config preflight missing required phrase: {phrase}")
    for template in PROVIDER_TEMPLATE_PATHS:
        if not (root / template).exists():
            result.add_error(f"missing provider env template: {template.as_posix()}")
    if not (root / BACKUP_OPERATOR_TEMPLATE_PATH).exists():
        result.add_error(f"missing backup operator template: {BACKUP_OPERATOR_TEMPLATE_PATH.as_posix()}")


def check_provider_files(root: Path, result: RunbookResult) -> None:
    worker = root / "backend" / "railway.worker.json"
    if not worker.exists():
        result.add_error("backend/railway.worker.json is missing")
    elif "python -m app.analysis_worker" not in read_text(worker):
        result.add_error("backend/railway.worker.json does not start app.analysis_worker")
    archive_worker = root / "backend" / "railway.audit-archive.json"
    if not archive_worker.exists():
        result.add_error("backend/railway.audit-archive.json is missing")
    elif "python -m app.audit_archive_worker" not in read_text(archive_worker):
        result.add_error("backend/railway.audit-archive.json does not start app.audit_archive_worker")
    vercel = root / "frontend" / "vercel.json"
    if not vercel.exists():
        result.add_error("frontend/vercel.json is missing")
    elif "/workspace/" not in read_text(vercel):
        result.add_error("frontend/vercel.json does not route legacy workspace pages to /workspace/")


def check_ci(root: Path, result: RunbookResult) -> None:
    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        result.add_error(".github/workflows/ci.yml is missing")
        return
    source = read_text(ci)
    if "tools/check_deploy_runbook.py" not in source:
        result.add_error("CI does not run tools/check_deploy_runbook.py")
    if "tools/check_provider_config.py" not in source:
        result.add_error("CI does not run tools/check_provider_config.py")
    if "tools/check_pilot_acceptance.py" not in source:
        result.add_error("CI does not run tools/check_pilot_acceptance.py")
    if "tools/check_error_telemetry.py" not in source:
        result.add_error("CI does not run tools/check_error_telemetry.py")
    if "tools/check_backup_recovery.py" not in source:
        result.add_error("CI does not run tools/check_backup_recovery.py")
    if "tools/check_data_lifecycle.py" not in source:
        result.add_error("CI does not run tools/check_data_lifecycle.py")
    if "tools/check_billing_lifecycle.py" not in source:
        result.add_error("CI does not run tools/check_billing_lifecycle.py")
    if "tools/check_company_team_foundation.py" not in source:
        result.add_error("CI does not run tools/check_company_team_foundation.py")
    if "tools/check_project_sharing.py" not in source:
        result.add_error("CI does not run tools/check_project_sharing.py")


def check_contract(root: Path) -> RunbookResult:
    result = RunbookResult(errors=[], warnings=[], deploy_order=[])
    deploy_order = parse_deploy_order(root, result)
    result.deploy_order = deploy_order
    check_runbook(root, result, deploy_order)
    check_env_matrix(root, result)
    check_config_preflight(root, result)
    check_provider_files(root, result)
    check_ci(root, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun production deployment runbook coverage.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to check.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    result = check_contract(root)
    payload: Dict[str, object] = {
        "ok": result.ok,
        "errors": result.errors,
        "warnings": result.warnings,
        "deploy_order": result.deploy_order,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for warning in result.warnings:
            print(f"[WARN] {warning}")
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Deployment runbook check {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
