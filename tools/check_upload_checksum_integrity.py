#!/usr/bin/env python3
"""Static contract checks for DevBareun v1.4.20 upload checksum integrity."""
from __future__ import annotations
import argparse
from pathlib import Path

REQUIRED = {
    "backend/app/file_validation.py": ["normalize_sha256_checksum", "SHA256_HEX_RE"],
    "backend/app/upload_routes.py": ["DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM", "checksum_status", "checksum_conflict"],
    "backend/app/services/parser_service.py": ["_verify_materialized_checksum", "checksum_mismatch", "verified_checksum"],
    "backend/app/services/analysis_job_service.py": ["_persist_file_integrity_state", "checksum_error"],
    "frontend/member-dashboard-app/src/pages/Upload.jsx": ["sha256File", "checksum"],
    "frontend/js/devbareun-api.js": ["calculateSha256", "checksum"],
    "database/2026_06_19_v1420_upload_checksum_integrity.sql": ["checksum_status", "verified_checksum", "idx_uploaded_files_checksum_status_v1420"],
    "docs/UPLOAD_CHECKSUM_INTEGRITY_V1420.md": ["SHA-256", "DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM"],
}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = []
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
    if not deploy_order.exists() or "2026_06_19_v1420_upload_checksum_integrity.sql" not in deploy_order.read_text(encoding="utf-8", errors="replace"):
        errors.append("database deploy order is missing v1.4.20 upload checksum migration")
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("Upload checksum integrity contract passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
