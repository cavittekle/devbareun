from __future__ import annotations

import importlib
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))


class BillingLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = importlib.import_module("app.services.billing_service")
        cls.CurrentUser = importlib.import_module("app.auth_dependencies").CurrentUser

    def user(self, *, role: str = "customer"):
        return self.CurrentUser(
            id="11111111-1111-1111-1111-111111111111",
            auth_user_id="11111111-1111-1111-1111-111111111111",
            email="user@example.test",
            role=role,
        )

    def test_active_subscription_ignores_expired_provider_period(self) -> None:
        now = self.service._now()
        rows = [
            {
                "id": "expired",
                "status": "active",
                "current_period_end": (now - timedelta(minutes=1)).isoformat(),
                "updated_at": now.isoformat(),
            },
            {
                "id": "active",
                "status": "active",
                "current_period_end": (now + timedelta(days=10)).isoformat(),
                "updated_at": now.isoformat(),
            },
        ]
        with patch.object(self.service, "is_configured", return_value=True), patch.object(self.service, "select_rows", return_value=rows):
            active = self.service._active_subscriptions(self.user())
        self.assertEqual([row["id"] for row in active], ["active"])

    def test_checkout_status_is_owner_scoped_and_safe(self) -> None:
        checkout = {
            "checkout_id": "checkout-safe",
            "owner_email": "user@example.test",
            "plan_code": "plus",
            "status": "provider_checkout_created",
            "checkout_url": "https://provider-secret.example.test",
            "customer_email": "user@example.test",
            "created_at": "2026-06-21T00:00:00+00:00",
            "updated_at": "2026-06-21T00:00:00+00:00",
        }
        payment = {"status": "checkout_created", "paid_at": None, "updated_at": "2026-06-21T00:00:00+00:00"}
        with patch.object(self.service, "is_configured", return_value=True), patch.object(self.service, "select_one", side_effect=[checkout, payment]):
            response = self.service.get_checkout_status(self.user(), "checkout-safe")
        serialized = json.dumps(response)
        self.assertNotIn("provider-secret", serialized)
        self.assertNotIn("user@example.test", serialized)
        self.assertEqual(response["poll_after_seconds"], 5)

    def test_checkout_fails_closed_without_payment_provider(self) -> None:
        with patch.object(self.service, "production_security_enabled", return_value=True):
            for plan in ("single", "plus", "pro"):
                with self.assertRaises(HTTPException) as ctx:
                    self.service.create_checkout_session(self.user(), plan, None, None, None)
                self.assertEqual(ctx.exception.status_code, 503)
                self.assertEqual(ctx.exception.detail["error"], "payments_unavailable")
                self.assertIn("info@devbareun.com", ctx.exception.detail["message"])

    def test_checkout_rejects_unknown_plan(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_checkout_session(self.user(), "enterprise", None, None, None)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_billing_contract_checker_passes(self) -> None:
        checker = importlib.import_module("check_billing_lifecycle")
        result = checker.check(ROOT)
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
