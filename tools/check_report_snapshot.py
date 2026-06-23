#!/usr/bin/env python3
"""Static contract checks for DevBareun v1.4.19 report snapshots."""
from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED = {
    "backend/app/services/report_service.py": [
        "REPORT_SNAPSHOT_VERSION",
        "normalize_report_format",
        "report_payload",
        "payload_sha256",
        "content_sha256",
        "record_report_download",
    ],
    "backend/app/report_routes.py": ["Cache-Control", "X-Content-Type-Options", "download_report"],
    "database/2026_06_19_v1419_report_snapshot_integrity.sql": [
        "payload_sha256",
        "content_sha256",
        "snapshot_version",
        "record_report_download",
        "grant execute on function public.record_report_download(uuid) to service_role",
    ],
    "docs/REPORT_SNAPSHOT_INTEGRITY_V1419.md": ["snapshot", "record_report_download", "legacy"],
    "frontend/member-dashboard-app/src/pages/Reports.jsx": ["Frozen analysis snapshot", "download_count"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check report snapshot integrity contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors: list[str] = []
    for rel, needles in REQUIRED.items():
        path = args.root / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel} missing: {needle}")
    deploy_order = args.root / "database" / "SUPABASE_DEPLOY_ORDER.md"
    if not deploy_order.exists() or "2026_06_19_v1419_report_snapshot_integrity.sql" not in deploy_order.read_text(encoding="utf-8", errors="replace"):
        errors.append("database deploy order is missing v1.4.19 report snapshot migration")
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("Report snapshot contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
