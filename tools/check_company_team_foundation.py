#!/usr/bin/env python3
"""Static contract checker for the v1.4.32 company team foundation."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence


@dataclass
class CheckResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check(root: Path) -> CheckResult:
    root = root.resolve()
    result = CheckResult()
    required = {
        "migration": root / "database/2026_06_21_v1432_company_team_foundation.sql",
        "service": root / "backend/app/services/company_team_service.py",
        "routes": root / "backend/app/company_team_routes.py",
        "document": root / "docs/COMPANY_TEAM_FOUNDATION_V1432.md",
        "client": root / "frontend/member-dashboard-app/src/api/client.js",
        "team_page": root / "frontend/member-dashboard-app/src/pages/Team.jsx",
    }
    for label, path in required.items():
        if not path.exists():
            result.errors.append(f"missing company-team {label}: {path.relative_to(root)}")

    if result.errors:
        return result

    migration = required["migration"].read_text(encoding="utf-8", errors="replace").lower()
    for expected in (
        "create table if not exists public.company_memberships",
        "create table if not exists public.company_invitations",
        "token_hash",
        "enable row level security",
        "ux_company_invitations_token_hash_v1432",
        "does not yet grant cross-user access",
    ):
        if expected not in migration:
            result.errors.append(f"company-team migration is missing expected contract text: {expected}")

    service = required["service"].read_text(encoding="utf-8", errors="replace")
    for expected in (
        "TEAM_ROLES",
        "invitation_hash",
        "token_hash",
        "manual",
        "company_workspace_for_user",
        "accept_invitation",
    ):
        if expected not in service:
            result.errors.append(f"company-team service is missing expected contract text: {expected}")
    if "raw_token" in service and '"token_hash": invitation_hash(raw_token)' not in service:
        result.errors.append("company-team service must persist a token hash instead of a raw token")

    routes = required["routes"].read_text(encoding="utf-8", errors="replace")
    for expected in (
        '@router.get("/workspace")',
        '@router.post("/workspace")',
        '@router.post("/invitations")',
        '@router.post("/invitations/accept")',
        '@router.post("/invitations/{invitation_id}/revoke")',
        '@router.patch("/members/{membership_id}")',
    ):
        if expected not in routes:
            result.errors.append(f"company-team route missing: {expected}")

    doc = required["document"].read_text(encoding="utf-8", errors="replace").lower()
    for expected in ("manual invite delivery", "does not yet grant cross-user access", "sha-256", "project-sharing"):
        if expected not in doc:
            result.errors.append(f"company-team documentation missing: {expected}")

    deploy_order = (root / "database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8", errors="replace")
    if "2026_06_21_v1432_company_team_foundation.sql" not in deploy_order:
        result.errors.append("deploy order missing v1.4.32 company-team migration")

    ci = root / ".github/workflows/ci.yml"
    if ci.exists() and "tools/check_company_team_foundation.py" not in ci.read_text(encoding="utf-8", errors="replace"):
        result.errors.append("CI does not run the company-team contract checker")

    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun company-team foundation contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = check(args.root)
    for warning in result.warnings:
        print(f"[WARN] {warning}")
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Company team contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
