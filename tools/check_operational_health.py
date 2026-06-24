#!/usr/bin/env python3
"""Static release contract for DevBareun v1.4.26 operational health."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

SERVICE = Path("backend/app/services/operations_health_service.py")
ROUTE = Path("backend/app/operations_routes.py")
MAIN = Path("backend/app/main.py")
ADMIN = Path("backend/app/saas_admin_routes.py")
SUPER_ADMIN = Path("backend/app/saas_super_admin_routes.py")
UI = Path("frontend/js/admin-panel.js")
HTML = Path("frontend/admin.html")
DOC = Path("docs/OPERATIONS_HEALTH_V1426.md")
CI = Path(".github/workflows/ci.yml")


@dataclass
class Result:
    errors: List[str] = field(default_factory=list)


def read(root: Path, path: Path, result: Result) -> str:
    target = root / path
    if not target.exists():
        result.errors.append(f"missing required file: {path.as_posix()}")
        return ""
    return target.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result()
    service = read(root, SERVICE, result)
    route = read(root, ROUTE, result)
    main = read(root, MAIN, result)
    admin = read(root, ADMIN, result)
    super_admin = read(root, SUPER_ADMIN, result)
    ui = read(root, UI, result)
    html = read(root, HTML, result)
    doc = read(root, DOC, result)
    ci = read(root, CI, result)

    for phrase in ("runtime_readiness_report", "analysis_operations_status", "audit_archive_operations_status", "analysis_worker_unavailable", "audit_archive_worker_unavailable", "operations_health_status"):
        if phrase not in service:
            result.errors.append(f"operations health service missing: {phrase}")
    if '@router.get("/health")' not in route or 'require_staff_permission(current_user, "operations")' not in route:
        result.errors.append("staff operations health route is missing capability guard")
    if "operations_router" not in main or "app.include_router(operations_router)" not in main:
        result.errors.append("main app does not register the operations health router")
    if '@router.get("/admin/operations-health")' not in admin or 'require_super_admin_user(authorization, "operations"' not in admin:
        result.errors.append("admin operations health endpoint is missing operations capability guard")
    if '@router.get("/super-admin/operations-health")' not in super_admin:
        result.errors.append("super-admin operations health alias is missing")
    if '"operations-health"' not in ui or "/api/super-admin/operations-health" not in ui or "renderOperationsHealth" not in ui:
        result.errors.append("admin UI does not expose operations health")
    if 'data-admin-tab="operations-health"' not in html:
        result.errors.append("admin HTML navigation does not expose operations health")
    for phrase in ("incident", "owner", "operator", "secrets"):
        if phrase not in doc.lower():
            result.errors.append(f"operational health documentation lacks: {phrase}")
    if "tools/check_operational_health.py" not in ci:
        result.errors.append("CI does not run operational health contract check")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    result = check(Path(args.root).resolve())
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Operational health contract {'passed' if not result.errors else 'failed'}: {len(result.errors)} error(s).")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
