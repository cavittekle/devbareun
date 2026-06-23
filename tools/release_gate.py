#!/usr/bin/env python3
"""DevBareun release gate.

Dependency-free checks that should pass before building a release package or
merging production changes. This complements pytest/build checks by verifying
repository hygiene, deploy-order references, env examples and obvious secret
leaks without requiring external services.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

ROOT_REQUIRED = [
    "AGENTS.md",
    "README.md",
    ".env.example",
    "backend/requirements.txt",
    "backend/app/main.py",
    "backend/app/version.py",
    "frontend/vercel.json",
    "frontend/member-dashboard-app/package.json",
    "frontend/member-dashboard-app/package-lock.json",
    "database/SUPABASE_DEPLOY_ORDER.md",
    "docs/CHANGELOG.md",
    "tools/validate_production_env.py",
    "tools/smoke_deploy.py",
    "tools/export_api_contract.py",
    "tools/check_frontend_assets.py",
    "tools/check_frontend_deploy_surface.py",
    "tools/check_template_manifest.py",
    "tools/check_database_contract.py",
    "tools/check_deploy_runbook.py",
    "tools/check_provider_config.py",
    "tools/check_analysis_idempotency.py",
    "tools/check_report_snapshot.py",
    "tools/check_upload_checksum_integrity.py",
    "tools/check_upload_security_screening.py",
    "tools/check_analysis_provenance.py",
    "tools/check_panel_access_boundaries.py",
    "tools/check_audit_integrity.py",
    "tools/check_operational_health.py",
    "tools/check_project_activity_timeline.py",
    "tools/check_pilot_acceptance.py",
    "tools/check_error_telemetry.py",
    "tools/backup_recovery.py",
    "tools/check_backup_recovery.py",
    "tools/pilot_acceptance.py",
    "docs/PILOT_ACCEPTANCE_V1427.md",
    "docs/ERROR_TELEMETRY_V1428.md",
    "docs/BACKUP_AND_RECOVERY_V1429.md",
    "docs/BILLING_LIFECYCLE_V1431.md",
    "docs/UPLOAD_CHECKSUM_INTEGRITY_V1420.md",
    "docs/UPLOAD_SECURITY_SCREENING_V1421.md",
    "docs/ANALYSIS_INPUT_PROVENANCE_V1422.md",
    "docs/PANEL_ACCESS_BOUNDARIES_V1423.md",
    "docs/AUDIT_INTEGRITY_V1424.md",
    "docs/OPERATIONS_HEALTH_V1426.md",
    "docs/PROJECT_ACTIVITY_TIMELINE_V1434.md",
    "database/2026_06_19_v1420_upload_checksum_integrity.sql",
    "database/2026_06_19_v1421_upload_security_screening.sql",
    "database/2026_06_19_v1422_analysis_input_provenance.sql",
    "database/2026_06_20_v1423_panel_access_boundaries.sql",
    "database/2026_06_20_v1424_audit_integrity.sql",
    "database/2026_06_21_v1431_billing_lifecycle_integrity.sql",
    "database/2026_06_21_v1434_project_activity_timeline.sql",
    "docs/ANALYSIS_IDEMPOTENCY_V1418.md",
    "database/2026_06_19_v1418_analysis_idempotency.sql",
    "docs/ANALYSIS_JOB_RECOVERY_V1417.md",
    "docs/ANALYSIS_WORKER_OPERATIONS_V1416.md",
    "database/2026_06_19_v1413_database_contract_bridge.sql",
    "docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md",
    "docs/DEPLOYMENT_ENV_MATRIX_V1414.md",
    "docs/PRODUCTION_CONFIG_PREFLIGHT_V1415.md",
    "deploy/env/README.md",
    "deploy/env/railway-web.env.template",
    "deploy/env/railway-worker.env.template",
    "deploy/env/vercel.env.template",
    "deploy/env/backup-operator.env.template",
    "frontend/assets/favicon.ico",
    "frontend/assets/favicon.png",
    "frontend/assets/apple-touch-icon.png",
    "frontend/assets/devbareun-logo-horizontal-white.svg",
    "frontend/assets/devbareun-logo-horizontal-black.svg",
    "frontend/assets/devbareun-logo-compact-white.svg",
    "frontend/assets/devbareun-symbol-white.svg",
    "frontend/assets/og-image.png",
]

FORBIDDEN_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".turbo",
}

FORBIDDEN_FILE_NAMES = {".DS_Store", "Thumbs.db"}

ENV_FILE_RE = re.compile(r"(^|/)\.env(\..+)?$")
ENV_ALLOWED_SUFFIXES = {".env.example", ".env.sample", ".env.template"}

SECRET_PATTERNS = [
    ("supabase_service_jwt", re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*=[^\S\r\n]*eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("supabase_jwt_secret", re.compile(r"SUPABASE_JWT_SECRET\s*=[^\S\r\n]*eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("postgres_url_with_password", re.compile(r"postgres(?:ql)?://[^\s:@]+:[^\s@]+@[^\s]+", re.I)),
    ("openai_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("lemonsqueezy_api_key", re.compile(r"LEMON_SQUEEZY_API_KEY\s*=[^\S\r\n]*[A-Za-z0-9_\-]{24,}")),
    ("upstash_token", re.compile(r"UPSTASH_REDIS_REST_TOKEN\s*=[^\S\r\n]*[A-Za-z0-9_\-]{24,}")),
]

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt", ".yml", ".yaml",
    ".sql", ".html", ".css", ".env", ".example", ".template", ".toml", ".ini", ".ps1", ".sh",
}

DEPLOY_ORDER_RE = re.compile(r"^\s*\d+\.\s+`([^`]+\.sql)`", re.M)
VERSION_RE = re.compile(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']')


@dataclass
class GateResult:
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        rel_parts = path.relative_to(root).parts
        if any(part in FORBIDDEN_DIR_NAMES for part in rel_parts[:-1]):
            continue
        if path.is_file():
            yield path


def is_text_candidate(path: Path) -> bool:
    if path.name in {"Procfile", ".gitignore", ".dockerignore", ".railwayignore"}:
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if path.name.endswith(".example"):
        return True
    return False


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required(root: Path, result: GateResult) -> None:
    for item in ROOT_REQUIRED:
        if not (root / item).exists():
            result.add_error(f"missing required release file: {item}")


def check_forbidden_paths(root: Path, result: GateResult, strict_package_tree: bool = False) -> None:
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_dir() and path.name in FORBIDDEN_DIR_NAMES:
            message = f"generated/cache directory should not be in release package: {rel}"
            if strict_package_tree:
                result.add_error(message)
            elif path.name != ".git":
                result.add_warning(message)
        elif path.is_file() and path.name in FORBIDDEN_FILE_NAMES:
            message = f"OS metadata file should not be in release package: {rel}"
            if strict_package_tree:
                result.add_error(message)
            else:
                result.add_warning(message)


def check_env_files(root: Path, result: GateResult) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if not ENV_FILE_RE.search(rel):
            continue
        if any(rel.endswith(suffix) for suffix in ENV_ALLOWED_SUFFIXES):
            continue
        result.add_error(f"committed runtime env file is not allowed: {rel}")


def check_secrets(root: Path, result: GateResult) -> None:
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        if not is_text_candidate(path):
            continue
        text = read_text(path)
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                lowered = value.lower()
                if "replace" in lowered or "example" in lowered or "your-project" in lowered:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                result.add_error(f"potential secret ({label}) in {rel}:{line}")


def extract_app_version(root: Path, result: GateResult) -> str:
    version_file = root / "backend" / "app" / "version.py"
    if not version_file.exists():
        result.add_error("backend/app/version.py is missing")
        return ""
    match = VERSION_RE.search(read_text(version_file))
    if not match:
        result.add_error("APP_VERSION could not be parsed from backend/app/version.py")
        return ""
    return match.group(1)


def check_version_docs(root: Path, result: GateResult) -> None:
    version = extract_app_version(root, result)
    if not version:
        return
    changelog = root / "docs" / "CHANGELOG.md"
    if changelog.exists() and f"v{version}" not in read_text(changelog):
        result.add_error(f"docs/CHANGELOG.md is missing v{version}")
    backend_env = root / "backend" / ".env.example"
    if backend_env.exists() and version not in read_text(backend_env):
        result.add_warning(f"backend/.env.example does not mention version {version}")


def check_deploy_order(root: Path, result: GateResult, require_all_migrations: bool = False) -> None:
    database = root / "database"
    order_path = database / "SUPABASE_DEPLOY_ORDER.md"
    if not order_path.exists():
        result.add_error("database/SUPABASE_DEPLOY_ORDER.md is missing")
        return
    text = read_text(order_path)
    listed = DEPLOY_ORDER_RE.findall(text)
    if not listed:
        result.add_error("database/SUPABASE_DEPLOY_ORDER.md does not list any SQL files")
        return
    seen: set[str] = set()
    for item in listed:
        if item in seen:
            result.add_error(f"duplicate deploy-order SQL reference: {item}")
        seen.add(item)
        if not (database / item).exists():
            result.add_error(f"deploy-order SQL file does not exist: {item}")
    required_latest = [
        "2026_05_29_v140_production_saas_core.sql",
        "2026_05_29_v140_part2_jobs_billing_reports.sql",
        "2026_06_08_v141_super_admin_workspace.sql",
        "2026_06_18_v142_canonical_api_bridge.sql",
        "2026_06_18_v145_analysis_worker.sql",
        "2026_06_19_v1413_database_contract_bridge.sql",
        "2026_06_19_v1416_analysis_worker_observability.sql",
        "2026_06_19_v1417_analysis_job_recovery.sql",
        "2026_06_19_v1418_analysis_idempotency.sql",
        "2026_06_19_v1419_report_snapshot_integrity.sql",
        "2026_06_19_v1420_upload_checksum_integrity.sql",
        "2026_06_19_v1421_upload_security_screening.sql",
        "2026_06_19_v1422_analysis_input_provenance.sql",
        "2026_06_20_v1423_panel_access_boundaries.sql",
        "2026_06_20_v1424_audit_integrity.sql",
        "2026_06_20_v1425_audit_archive_outbox.sql",
        "2026_06_21_v1430_data_lifecycle_requests.sql",
        "2026_06_21_v1431_billing_lifecycle_integrity.sql",
        "2026_06_21_v1432_company_team_foundation.sql",
        "2026_06_21_v1433_project_sharing.sql",
    ]
    for item in required_latest:
        if item not in seen:
            result.add_error(f"deploy order missing required production migration: {item}")
    if require_all_migrations:
        all_migrations = sorted(path.name for path in database.glob("20*.sql"))
        for item in all_migrations:
            if item not in seen:
                result.add_error(f"deploy order missing migration under --require-all-migrations: {item}")


def check_frontend_package(root: Path, result: GateResult) -> None:
    package_json = root / "frontend" / "member-dashboard-app" / "package.json"
    package_lock = root / "frontend" / "member-dashboard-app" / "package-lock.json"
    if not package_json.exists() or not package_lock.exists():
        return
    try:
        pkg = json.loads(read_text(package_json))
        lock = json.loads(read_text(package_lock))
    except json.JSONDecodeError as exc:
        result.add_error(f"frontend package metadata is invalid JSON: {exc}")
        return
    if "build" not in (pkg.get("scripts") or {}):
        result.add_error("frontend/member-dashboard-app/package.json is missing scripts.build")
    if pkg.get("name") and lock.get("name") and pkg.get("name") != lock.get("name"):
        result.add_warning("frontend package.json and package-lock.json names differ")


def check_ci(root: Path, result: GateResult) -> None:
    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        result.add_warning(".github/workflows/ci.yml is missing")
        return
    source = read_text(ci)
    for expected in ("tools/release_gate.py", "tools/validate_production_env.py", "tools/export_api_contract.py", "tools/check_frontend_assets.py", "tools/check_frontend_deploy_surface.py", "tools/check_template_manifest.py", "tools/check_database_contract.py", "tools/check_deploy_runbook.py", "tools/check_provider_config.py", "tools/check_analysis_idempotency.py", "tools/check_report_snapshot.py", "tools/check_upload_checksum_integrity.py", "tools/check_upload_security_screening.py", "tools/check_analysis_provenance.py", "tools/check_panel_access_boundaries.py", "tools/check_audit_integrity.py", "tools/check_audit_archive_outbox.py", "tools/check_operational_health.py", "tools/check_data_lifecycle.py", "tools/check_billing_lifecycle.py", "tools/check_company_team_foundation.py", "tools/check_project_sharing.py", "tools/check_project_activity_timeline.py", "pytest", "npm ci"):
        if expected not in source:
            result.add_warning(f"CI workflow does not mention {expected}")


def run(root: Path, require_all_migrations: bool = False, strict_package_tree: bool = False) -> GateResult:
    result = GateResult(errors=[], warnings=[])
    check_required(root, result)
    check_forbidden_paths(root, result, strict_package_tree=strict_package_tree)
    check_env_files(root, result)
    check_secrets(root, result)
    check_version_docs(root, result)
    check_deploy_order(root, result, require_all_migrations=require_all_migrations)
    check_frontend_package(root, result)
    check_ci(root, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run DevBareun release-gate checks.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to check.")
    parser.add_argument("--require-all-migrations", action="store_true", help="Require every database/20*.sql file to be listed in deploy order.")
    parser.add_argument("--strict-package-tree", action="store_true", help="Treat generated/cache directories as errors instead of warnings.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    result = run(root, require_all_migrations=args.require_all_migrations, strict_package_tree=args.strict_package_tree)
    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, indent=2))
    else:
        for warning in result.warnings:
            print(f"[WARN] {warning}")
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Release gate {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
