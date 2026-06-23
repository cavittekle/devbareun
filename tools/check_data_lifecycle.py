#!/usr/bin/env python3
"""Static release contract for DevBareun privacy/data lifecycle controls."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

REQUIRED_FILES = (
    "backend/app/data_lifecycle_routes.py",
    "backend/app/services/data_lifecycle_service.py",
    "database/2026_06_21_v1430_data_lifecycle_requests.sql",
    "docs/DATA_LIFECYCLE_V1430.md",
)
REQUIRED_ENV_KEYS = (
    "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS",
    "DEVBAREUN_ERASURE_GRACE_DAYS",
    "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS",
    "DEVBAREUN_AUTO_PURGE_ENABLED",
)
REQUIRED_ROUTE_SNIPPETS = (
    '@router.get("/policy")',
    '@router.get("/requests")',
    '@router.post("/export-requests")',
    '@router.post("/erasure-requests")',
    '@router.post("/requests/{request_id}/cancel")',
)


@dataclass
class CheckResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> CheckResult:
    root = root.resolve()
    result = CheckResult()
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            result.errors.append(f"missing data lifecycle file: {relative}")

    routes = root / "backend/app/data_lifecycle_routes.py"
    if routes.exists():
        source = read(routes)
        for expected in REQUIRED_ROUTE_SNIPPETS:
            if expected not in source:
                result.errors.append(f"privacy route is missing: {expected}")
        if "ERASURE_CONFIRMATION" not in source:
            result.errors.append("erasure confirmation is not enforced by privacy routes")
        if "record_audit_event" not in source:
            result.errors.append("privacy mutations are missing audit recording")

    policy = root / "backend/app/services/data_lifecycle_service.py"
    if policy.exists():
        source = read(policy)
        for expected in ("soft_delete_schedule", "customer_safe_row", "admin_safe_row", "automatic_physical_purge"):
            if expected not in source:
                result.errors.append(f"data lifecycle service missing {expected}")
        if "export_payload" not in source or "storage_path" not in source:
            result.errors.append("privacy response redaction fields are incomplete")

    migration = root / "database/2026_06_21_v1430_data_lifecycle_requests.sql"
    if migration.exists():
        source = read(migration).lower()
        for expected in (
            "create table if not exists public.data_lifecycle_requests",
            "enable row level security",
            "data_lifecycle_requests_no_direct_browser_access_v1430",
            "guard_data_lifecycle_request_v1430",
            "purge_after_at",
            "retention_status",
        ):
            if expected not in source:
                result.errors.append(f"data lifecycle migration missing {expected}")

    access = root / "backend/app/access_control.py"
    if access.exists():
        source = read(access)
        if '"privacy"' not in source:
            result.errors.append("canonical access-control policy lacks privacy capability")
        support_line = next((line for line in source.splitlines() if '"support":' in line), "")
        if '"privacy"' in support_line:
            result.errors.append("support role must not receive owner privacy capability")

    main = root / "backend/app/main.py"
    if main.exists() and "data_lifecycle_router" not in read(main):
        result.errors.append("main application does not register data lifecycle router")

    client = root / "frontend/member-dashboard-app/src/api/client.js"
    if client.exists():
        source = read(client)
        for expected in (
            "privacyPolicy",
            "privacyRequests",
            "requestDataExport",
            "requestDataErasure",
            "cancelPrivacyRequest",
            "/api/privacy/erasure-requests",
        ):
            if expected not in source:
                result.errors.append(f"workspace API client is missing privacy operation: {expected}")
    else:
        result.errors.append("workspace API client is missing")

    settings = root / "frontend/member-dashboard-app/src/pages/Settings.jsx"
    if settings.exists():
        source = read(settings)
        for expected in ("Data lifecycle", "ERASE MY DATA", "requestDataExport", "requestDataErasure"):
            if expected not in source:
                result.errors.append(f"workspace settings does not expose guarded privacy workflow: {expected}")
    else:
        result.errors.append("workspace settings page is missing")

    order = root / "database/SUPABASE_DEPLOY_ORDER.md"
    if order.exists() and "2026_06_21_v1430_data_lifecycle_requests.sql" not in read(order):
        result.errors.append("Supabase deploy order omits v1.4.30 migration")

    for env_file in (
        root / "backend/.env.example",
        root / "deploy/env/railway-web.env.template",
        root / "deploy/env/railway-worker.env.template",
        root / "deploy/env/railway-audit-archive.env.template",
    ):
        if not env_file.exists():
            result.errors.append(f"missing provider template: {env_file.relative_to(root)}")
            continue
        env_text = read(env_file)
        for key in REQUIRED_ENV_KEYS:
            if not re.search(rf"^{re.escape(key)}=", env_text, flags=re.MULTILINE):
                result.errors.append(f"{env_file.relative_to(root)} is missing {key}")

    ci = root / ".github/workflows/ci.yml"
    if ci.exists() and "tools/check_data_lifecycle.py" not in read(ci):
        result.errors.append("CI does not run data lifecycle contract checker")
    gate = root / "tools/release_gate.py"
    if gate.exists() and "tools/check_data_lifecycle.py" not in read(gate):
        result.errors.append("release gate does not require data lifecycle contract checker")

    docs = root / "docs/DATA_LIFECYCLE_V1430.md"
    if docs.exists():
        source = read(docs).lower()
        if "does **not**" not in source and "does not" not in source:
            result.errors.append("data lifecycle documentation must state the destructive automation boundary")

    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun data lifecycle release contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = check(args.root)
    for warning in result.warnings:
        print(f"[WARN] {warning}")
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Data lifecycle contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
