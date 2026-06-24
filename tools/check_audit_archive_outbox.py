#!/usr/bin/env python3
"""Static release contract for DevBareun v1.4.25 audit archive outbox."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

MIGRATION = Path("database/2026_06_20_v1425_audit_archive_outbox.sql")
DOC = Path("docs/AUDIT_ARCHIVE_OUTBOX_V1425.md")
SERVICE = Path("backend/app/services/audit_archive_service.py")
WORKER = Path("backend/app/audit_archive_worker.py")
RAILWAY = Path("backend/railway.audit-archive.json")
ADMIN = Path("backend/app/saas_admin_routes.py")
SUPER_ADMIN = Path("backend/app/saas_super_admin_routes.py")
ADMIN_UI = Path("frontend/js/admin-panel.js")
TEMPLATE = Path("deploy/env/railway-audit-archive.env.template")
CI = Path(".github/workflows/ci.yml")
DEPLOY_ORDER = Path("database/SUPABASE_DEPLOY_ORDER.md")


@dataclass
class Result:
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def read(root: Path, path: Path, result: Result) -> str:
    target = root / path
    if not target.exists():
        result.errors.append(f"missing required file: {path.as_posix()}")
        return ""
    return target.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result()
    migration = read(root, MIGRATION, result)
    doc = read(root, DOC, result)
    service = read(root, SERVICE, result)
    worker = read(root, WORKER, result)
    railway = read(root, RAILWAY, result)
    admin = read(root, ADMIN, result)
    super_admin = read(root, SUPER_ADMIN, result)
    ui = read(root, ADMIN_UI, result)
    template = read(root, TEMPLATE, result)
    ci = read(root, CI, result)
    deploy_order = read(root, DEPLOY_ORDER, result)

    for phrase in (
        "audit_archive_outbox",
        "enqueue_audit_archive_outbox_v1425",
        "claim_audit_archive_outbox",
        "record_audit_archive_delivery",
        "record_audit_archive_failure",
        "retry_audit_archive_item",
        "audit_archive_status",
        "lease_token",
        "dead_lettered",
        "audit_archive_worker_heartbeats",
    ):
        if phrase not in migration:
            result.errors.append(f"v1.4.25 migration missing: {phrase}")
    for phrase in (
        "drain_audit_archive_once",
        "audit_archive_delivery_ready",
        "X-DevBareun-Audit-Signature",
        "record_audit_archive_worker_heartbeat",
        "retry_audit_archive_item",
    ):
        if phrase not in service:
            result.errors.append(f"audit archive service missing: {phrase}")
    if "python -m app.audit_archive_worker" not in railway or "def main" not in worker or "drain_audit_archive_once" not in worker:
        result.errors.append("Railway audit archive worker command is incomplete")
    if '@router.get("/admin/audit-archive")' not in admin or '@router.post("/admin/audit-archive/{archive_id}/retry")' not in admin:
        result.errors.append("admin audit archive endpoints are missing")
    if '@router.get("/super-admin/audit-archive")' not in super_admin or '"/super-admin/audit-archive/{archive_id}/retry"' not in super_admin:
        result.errors.append("super-admin audit archive endpoints are missing")
    if '"audit-archive"' not in ui or "/api/super-admin/audit-archive" not in ui:
        result.errors.append("admin UI does not expose audit archive status")
    for phrase in ("DEVBAREUN_AUDIT_ARCHIVE_MODE", "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL", "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET"):
        if phrase not in template:
            result.errors.append(f"archive worker template missing: {phrase}")
    if MIGRATION.name not in deploy_order:
        result.errors.append("v1.4.25 migration is missing from deploy order")
    if "tools/check_audit_archive_outbox.py" not in ci:
        result.errors.append("CI does not run audit archive outbox contract check")
    if "transactional" not in doc.lower() or "dead-letter" not in doc.lower() or "hmac" not in doc.lower():
        result.errors.append("audit archive documentation lacks transactional/dead-letter/HMAC scope")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    result = check(Path(args.root).resolve())
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Audit archive outbox contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
