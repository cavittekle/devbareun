#!/usr/bin/env python3
"""Static release contract for DevBareun audit integrity v1.4.24."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

MIGRATION = Path("database/2026_06_20_v1424_audit_integrity.sql")
DOC = Path("docs/AUDIT_INTEGRITY_V1424.md")
SERVICE = Path("backend/app/services/audit_service.py")
CONTEXT = Path("backend/app/audit_context.py")
MAIN = Path("backend/app/main.py")
COMMON = Path("backend/app/saas_common.py")
ADMIN = Path("backend/app/saas_admin_routes.py")
SUPER_ADMIN = Path("backend/app/saas_super_admin_routes.py")
ADMIN_UI = Path("frontend/js/admin-panel.js")
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
    service = read(root, SERVICE, result)
    context = read(root, CONTEXT, result)
    main = read(root, MAIN, result)
    common = read(root, COMMON, result)
    admin = read(root, ADMIN, result)
    super_admin = read(root, SUPER_ADMIN, result)
    admin_ui = read(root, ADMIN_UI, result)
    ci = read(root, CI, result)
    deploy_order = read(root, DEPLOY_ORDER, result)

    for phrase in (
        "append_audit_event",
        "audit_integrity_status",
        "audit_logs_immutable_v1424",
        "reject_audit_log_mutation_v1424",
        "pg_advisory_xact_lock",
        "integrity_version",
        "event_hash",
        "previous_event_hash",
        "metadata_sha256",
    ):
        if phrase not in migration:
            result.errors.append(f"v1.4.24 migration missing: {phrase}")
    for phrase in ("sanitize_metadata", "metadata_sha256", "record_audit_event", "AuditWriteError"):
        if phrase not in service:
            result.errors.append(f"audit service missing: {phrase}")
    if "begin_request_context" not in context or "current_audit_context" not in context:
        result.errors.append("request audit context helpers are incomplete")
    if "begin_request_context(request)" not in main or 'response.headers["X-Request-ID"]' not in main:
        result.errors.append("request-id middleware is not wired into FastAPI")
    if "record_audit_event(admin" not in common:
        result.errors.append("shared admin audit helper does not use the durable audit service")
    if '@router.get("/admin/audit-integrity")' not in admin:
        result.errors.append("admin audit-integrity endpoint is missing")
    if '@router.get("/super-admin/audit-integrity")' not in super_admin:
        result.errors.append("super-admin audit-integrity endpoint is missing")
    if '"audit-integrity"' not in admin_ui or "/api/super-admin/audit-integrity" not in admin_ui:
        result.errors.append("admin UI does not expose audit integrity status")
    if MIGRATION.name not in deploy_order:
        result.errors.append("v1.4.24 migration is missing from deploy order")
    if "tools/check_audit_integrity.py" not in ci:
        result.errors.append("CI does not run audit-integrity contract check")
    if "append-only" not in doc.lower() or "tamper" not in doc.lower():
        result.errors.append("audit-integrity documentation lacks append-only/tamper-evidence scope")
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
        print(f"Audit integrity contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
