#!/usr/bin/env python3
"""Static release contract for DevBareun panel access boundaries v1.4.23."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

MIGRATION = Path("database/2026_06_20_v1423_panel_access_boundaries.sql")
DOC = Path("docs/PANEL_ACCESS_BOUNDARIES_V1423.md")
POLICY = Path("backend/app/access_control.py")
AUTH = Path("backend/app/auth_dependencies.py")
ANALYSIS = Path("backend/app/analysis_routes.py")
UPLOADS = Path("backend/app/upload_routes.py")
REPORTS = Path("backend/app/services/report_service.py")
JOBS = Path("backend/app/services/analysis_job_service.py")
ADMIN = Path("backend/app/saas_admin_routes.py")
SUPER_ADMIN_DOC = Path("docs/SUPER_ADMIN_WORKSPACE.md")
CI = Path(".github/workflows/ci.yml")
DEPLOY_ORDER = Path("database/SUPABASE_DEPLOY_ORDER.md")


@dataclass
class Result:
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def read(root: Path, relative: Path, result: Result) -> str:
    path = root / relative
    if not path.exists():
        result.errors.append(f"missing required file: {relative.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result()
    migration = read(root, MIGRATION, result)
    doc = read(root, DOC, result)
    policy = read(root, POLICY, result)
    auth = read(root, AUTH, result)
    analysis = read(root, ANALYSIS, result)
    uploads = read(root, UPLOADS, result)
    reports = read(root, REPORTS, result)
    jobs = read(root, JOBS, result)
    admin = read(root, ADMIN, result)
    super_admin_doc = read(root, SUPER_ADMIN_DOC, result)
    ci = read(root, CI, result)
    deploy_order = read(root, DEPLOY_ORDER, result)

    for role in ("customer", "owner", "support", "analyst", "finance", "operator"):
        if f'"{role}"' not in policy:
            result.errors.append(f"canonical policy missing role: {role}")
    for capability in ("projects", "uploads", "reports", "payments", "credits", "operations"):
        if f'"{capability}"' not in policy:
            result.errors.append(f"canonical policy missing capability: {capability}")
    for phrase in ("can_access_project_scope", "can_operate_analysis_jobs", "normalize_role"):
        if phrase not in policy:
            result.errors.append(f"canonical policy missing helper: {phrase}")
    if "require_project_owner" not in auth or "section: str = \"projects\"" not in auth:
        result.errors.append("project guard is not capability-bound")
    if 'require_project_owner(project_id, current_user, section="projects")' not in analysis:
        result.errors.append("analysis routes do not declare projects capability")
    if 'require_staff_permission(current_user, "operations")' not in analysis:
        result.errors.append("analysis operations are not permission-bound")
    if 'section="uploads"' not in uploads or 'can_access_project_scope(user.role, "uploads")' not in uploads:
        result.errors.append("upload routes do not enforce uploads capability")
    if 'can_access_project_scope(user.role, "reports")' not in reports:
        result.errors.append("report service does not enforce reports capability")
    if 'can_operate_analysis_jobs(actor.role)' not in jobs:
        result.errors.append("job recovery does not enforce operations capability")
    if "Staff accounts must be managed through the staff-management endpoint." not in admin:
        result.errors.append("customer status endpoint does not protect staff accounts")
    for phrase in ("users_profile_canonical_role_check", "idx_users_profile_active_role", "role IN ('customer', 'owner', 'support', 'analyst', 'finance', 'operator')"):
        if phrase not in migration:
            result.errors.append(f"v1.4.23 migration missing: {phrase}")
    if MIGRATION.name not in deploy_order:
        result.errors.append("v1.4.23 migration is missing from deploy order")
    if "Analysis operations / recovery" not in super_admin_doc:
        result.errors.append("Super Admin role matrix lacks operations row")
    if "tools/check_panel_access_boundaries.py" not in ci:
        result.errors.append("CI does not run panel access boundary check")
    if "generic “staff” bypass" not in doc and "generic \"staff\" bypass" not in doc:
        result.errors.append("panel access documentation does not state broad-staff bypass removal")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(Path(args.root).resolve())
    if args.json:
        import json
        print(json.dumps({"ok": result.ok, "errors": result.errors}, indent=2))
    else:
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Panel access boundary contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
