#!/usr/bin/env python3
"""Static release contract for DevBareun billing lifecycle integrity.

The check intentionally does not call any payment provider or Supabase. No
online payment provider is connected: it verifies that checkout requests fail
closed with a clear message, that no provider webhook route is exposed, and
that customer-safe status polling remains wired into the deployable source tree.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

REQUIRED_FILES = (
    "backend/app/services/billing_service.py",
    "backend/app/billing_routes.py",
    "database/2026_06_21_v1431_billing_lifecycle_integrity.sql",
    "docs/BILLING_LIFECYCLE_V1431.md",
    "frontend/member-dashboard-app/src/pages/PaymentStatus.jsx",
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
            result.errors.append(f"missing billing lifecycle file: {relative}")

    service = root / "backend/app/services/billing_service.py"
    if service.exists():
        source = read(service)
        for expected in ("get_checkout_status", "payments_unavailable", "PAYMENTS_UNAVAILABLE_MESSAGE"):
            if expected not in source:
                result.errors.append(f"billing service is missing checkout guard: {expected}")
        if "lemon" in source.lower():
            result.errors.append("billing service must not reference a removed payment provider")

    routes = root / "backend/app/billing_routes.py"
    if routes.exists():
        source = read(routes)
        if '@router.get("/checkouts/{checkout_id}")' not in source:
            result.errors.append("billing routes are missing checkout lifecycle status endpoint")
        if "get_checkout_status" not in source:
            result.errors.append("billing status endpoint is not delegated to the service")

    for rel in ("backend/app/billing_routes.py", "backend/app/saas_public_routes.py"):
        path = root / rel
        if path.exists() and re.search(r'@router\.post\("[^"]*webhook"\)', read(path)):
            result.errors.append(f"{rel} exposes a payment webhook route but no payment provider is connected")

    migration = root / "database/2026_06_21_v1431_billing_lifecycle_integrity.sql"
    if migration.exists():
        source = read(migration).lower()
        for expected in (
            "claim_payment_webhook_event",
            "complete_payment_webhook_event",
            "processing_status",
            "dead_lettered",
            "source_event_id",
            "last_provider_event_id",
            "drop function if exists public.claim_payment_webhook_event",
            "revoke all on function public.claim_payment_webhook_event",
        ):
            if expected not in source:
                result.errors.append(f"billing lifecycle migration missing {expected}")

    order = root / "database/SUPABASE_DEPLOY_ORDER.md"
    if order.exists() and migration.name not in read(order):
        result.errors.append("Supabase deploy order omits v1.4.31 billing lifecycle migration")

    client = root / "frontend/member-dashboard-app/src/api/client.js"
    status = root / "frontend/member-dashboard-app/src/pages/PaymentStatus.jsx"
    if client.exists() and "checkoutStatus" not in read(client):
        result.errors.append("workspace API client lacks checkoutStatus")
    if status.exists():
        source = read(status)
        for expected in ("workspaceApi.checkoutStatus", "maxAttempts", "poll_after_seconds"):
            if expected not in source:
                result.errors.append(f"payment status view lacks lifecycle polling guard: {expected}")

    docs = root / "docs/BILLING_LIFECYCLE_V1431.md"
    if docs.exists():
        source = read(docs).lower()
        for expected in ("does not", "payments_unavailable", "info@devbareun.com"):
            if expected not in source:
                result.errors.append(f"billing lifecycle documentation missing required boundary: {expected}")

    ci = root / ".github/workflows/ci.yml"
    gate = root / "tools/release_gate.py"
    if ci.exists() and "tools/check_billing_lifecycle.py" not in read(ci):
        result.errors.append("CI does not run billing lifecycle contract checker")
    if gate.exists() and "tools/check_billing_lifecycle.py" not in read(gate):
        result.errors.append("release gate does not require billing lifecycle contract checker")

    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun billing lifecycle release contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = check(args.root)
    for warning in result.warnings:
        print(f"[WARN] {warning}")
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Billing lifecycle contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
