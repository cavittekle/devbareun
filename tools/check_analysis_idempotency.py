#!/usr/bin/env python3
"""Static contract checks for DevBareun v1.4.18 analysis idempotency."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

REQUIRED = {
    "backend/app/analysis_routes.py": ["Idempotency-Key", "idempotency_key=idempotency_key"],
    "backend/app/services/analysis_job_service.py": ["_find_idempotent_job", "_find_active_job_for_project", "_recover_persisted_result", "billing_status"],
    "backend/app/services/billing_service.py": ["consume_analysis_usage_once", "Atomic analysis usage accounting"],
    "backend/app/production_store.py": ["def call_rpc"],
    "frontend/member-dashboard-app/src/api/client.js": ["Idempotency-Key", "createIdempotencyKey"],
    "frontend/js/devbareun-api.js": ["Idempotency-Key", "createIdempotencyKey"],
    "database/2026_06_19_v1418_analysis_idempotency.sql": ["analysis_usage_ledger", "consume_analysis_usage_once", "idx_analysis_jobs_owner_idempotency_v1418"],
    "docs/ANALYSIS_IDEMPOTENCY_V1418.md": ["Idempotency-Key", "analysis_usage_ledger"],
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
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1
    print("Analysis idempotency contract passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
