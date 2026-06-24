#!/usr/bin/env python3
"""Static release contract for DevBareun billing lifecycle integrity.

The check intentionally does not call Lemon Squeezy or Supabase. It verifies
that checkout correlation, retry-safe payment event handling, provider-period
usage reset, configuration parity and customer-safe status polling remain wired
into the deployable source tree.
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
REQUIRED_ENV_KEY = "DEVBAREUN_PAYMENT_WEBHOOK_MAX_ATTEMPTS"


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
        for expected in (
            "checkout_id = str(uuid4())",
            '"checkout_id": checkout_id',
            "_record_checkout_session",
            "get_checkout_status",
            "claim_payment_webhook_event",
            "complete_payment_webhook_event",
            "_event_fingerprint",
            "_provider_period",
            "_checkout_owner_context",
            "refund_review_required",
            "payment_webhook_processing_failed",
        ):
            if expected not in source:
                result.errors.append(f"billing service is missing lifecycle guard: {expected}")
        if '"p_owner_email": owner_email' in source:
            result.errors.append("payment event claim must not pass raw owner email to the webhook RPC")
        if "raw_body" in source and "payload":
            # Informational only: raw_body is required for signature/hash input.
            pass

    routes = root / "backend/app/billing_routes.py"
    if routes.exists():
        source = read(routes)
        if '@router.get("/checkouts/{checkout_id}")' not in source:
            result.errors.append("billing routes are missing checkout lifecycle status endpoint")
        if "get_checkout_status" not in source:
            result.errors.append("billing status endpoint is not delegated to the service")

    compat = root / "backend/app/saas_public_routes.py"
    if compat.exists():
        source = read(compat)
        webhook = re.search(r'@router\.post\("/payments/webhook"\).*?(?=\n@router|\Z)', source, flags=re.S)
        if not webhook or "except Exception" in webhook.group(0):
            result.errors.append("compatibility webhook must not convert transient processing failures into HTTP 400")

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

    for rel in (
        "backend/.env.example",
        "deploy/env/railway-web.env.template",
        "deploy/env/railway-worker.env.template",
        "deploy/env/railway-audit-archive.env.template",
    ):
        path = root / rel
        if not path.exists():
            result.errors.append(f"missing provider env template: {rel}")
        elif not re.search(rf"^{re.escape(REQUIRED_ENV_KEY)}=", read(path), flags=re.M):
            result.errors.append(f"{rel} is missing {REQUIRED_ENV_KEY}")

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
        for expected in ("does not", "retry", "raw provider payload", "refund", "devbareun_payment_webhook_max_attempts"):
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
