from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
import os
import sys
import time
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
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": ""}), patch.object(self.service, "production_security_enabled", return_value=True):
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

    # --- Polar -------------------------------------------------------------

    SECRET = "polar_whs_test_secret"

    def signed_headers(self, body: bytes, *, msg_id: str = "msg_1", timestamp: int | None = None, secret: str | None = None):
        ts = str(timestamp if timestamp is not None else int(time.time()))
        digest = hmac.new((secret or self.SECRET).encode(), f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()
        return {"webhook-id": msg_id, "webhook-timestamp": ts, "webhook-signature": "v1," + base64.b64encode(digest).decode()}

    def test_checkout_returns_polar_link_with_reference(self) -> None:
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": self.SECRET}), patch.object(self.service, "is_configured", return_value=False):
            single = self.service.create_checkout_session(self.user(), "single", None, None, None)
            annual = self.service.create_subscription_checkout(self.user(), "pro", None, None, "annual")
            monthly = self.service.create_subscription_checkout(self.user(), "plus", None, None, None)
        self.assertTrue(single["checkout_url"].startswith(self.service.POLAR_CHECKOUT_LINKS[("single", "one_time")][1] + "?"))
        self.assertIn("reference_id=" + single["checkout_id"], single["checkout_url"])
        self.assertIn("customer_email=user%40example.test", single["checkout_url"])
        self.assertEqual(single["provider"], "polar")
        self.assertTrue(annual["checkout_url"].startswith(self.service.POLAR_CHECKOUT_LINKS[("pro", "annual")][1]))
        self.assertEqual(monthly["billing_cycle"], "monthly")
        self.assertTrue(monthly["checkout_url"].startswith(self.service.POLAR_CHECKOUT_LINKS[("plus", "monthly")][1]))

    def test_polar_signature_verification(self) -> None:
        body = b'{"type":"order.paid"}'
        headers = self.signed_headers(body)
        self.service.verify_polar_signature(body, headers, self.SECRET)
        for bad in (
            self.signed_headers(body, secret="other"),
            self.signed_headers(body, timestamp=int(time.time()) - 3600),
            {**headers, "webhook-signature": ""},
        ):
            with self.assertRaises(HTTPException) as ctx:
                self.service.verify_polar_signature(body, bad, self.SECRET)
            self.assertEqual(ctx.exception.status_code, 400)
        with self.assertRaises(HTTPException):
            self.service.verify_polar_signature(body + b" ", headers, self.SECRET)

    def test_standard_webhooks_secret_format(self) -> None:
        key = b"0123456789abcdef0123456789abcdef"
        secret = "whsec_" + base64.b64encode(key).decode()
        body = b'{"type":"order.paid"}'
        ts = str(int(time.time()))
        digest = hmac.new(key, f"msg_2.{ts}.".encode() + body, hashlib.sha256).digest()
        headers = {"webhook-id": "msg_2", "webhook-timestamp": ts, "webhook-signature": "v1," + base64.b64encode(digest).decode()}
        self.service.verify_polar_signature(body, headers, secret)
        # Legacy derivation (UTF-8 bytes of the whole secret) is still accepted.
        self.service.verify_polar_signature(body, self.signed_headers(body, secret=secret), secret)

    def test_webhook_requires_secret(self) -> None:
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": ""}):
            with self.assertRaises(HTTPException) as ctx:
                self.service.handle_webhook(b"{}", {})
        self.assertEqual(ctx.exception.status_code, 503)

    def _order_event(self, plan: str, cycle: str, *, subscription: dict | None = None) -> bytes:
        data = {
            "id": "order_1",
            "checkout_id": "polar_checkout_1",
            "total_amount": 2900,
            "currency": "usd",
            "metadata": {"reference_id": "our-checkout-1", "devbareun_plan": plan, "billing_cycle": cycle},
            "product": {"metadata": {"devbareun_plan": plan, "billing_cycle": cycle}},
            "customer": {"email": "Buyer@Example.test"},
            "subscription_id": (subscription or {}).get("id"),
            "subscription": subscription,
        }
        return json.dumps({"type": "order.paid", "data": data}).encode()

    def test_order_paid_single_grants_one_credit_for_checkout_owner(self) -> None:
        body = self._order_event("single", "one_time")
        checkout_row = {"checkout_id": "our-checkout-1", "owner_email": "user@example.test", "user_id": "11111111-1111-1111-1111-111111111111", "plan_code": "single"}
        inserted = []

        def select_one(table, filters):
            if table == "checkout_sessions":
                return checkout_row
            return None

        def insert_row(table, payload):
            inserted.append((table, payload))
            return {"id": "credit-1", **payload}

        rpc_calls = []
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": self.SECRET}), \
                patch.object(self.service, "is_configured", return_value=True), \
                patch.object(self.service, "select_one", side_effect=select_one), \
                patch.object(self.service, "insert_row", side_effect=insert_row), \
                patch.object(self.service, "first_update", return_value={}), \
                patch.object(self.service, "call_rpc", side_effect=lambda name, params: rpc_calls.append((name, params)) or {"claimed": True}):
            result = self.service.handle_webhook(body, self.signed_headers(body))
        self.assertEqual(result["outcome"], "credit_granted")
        credits = [payload for table, payload in inserted if table == "analysis_credits"]
        self.assertEqual(len(credits), 1)
        self.assertEqual(credits[0]["owner_email"], "user@example.test")
        self.assertEqual(credits[0]["remaining"], 1)
        self.assertEqual(rpc_calls[0][0], "claim_payment_webhook_event")
        self.assertEqual(rpc_calls[0][1]["p_provider"], "polar")
        self.assertNotIn("Buyer@Example.test", json.dumps(rpc_calls))

    def test_duplicate_webhook_is_ignored(self) -> None:
        body = self._order_event("single", "one_time")
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": self.SECRET}), \
                patch.object(self.service, "is_configured", return_value=True), \
                patch.object(self.service, "select_one", return_value=None), \
                patch.object(self.service, "insert_row") as insert_row, \
                patch.object(self.service, "call_rpc", return_value={"claimed": False, "state": "processed"}):
            result = self.service.handle_webhook(body, self.signed_headers(body))
        self.assertEqual(result["status"], "duplicate_ignored")
        insert_row.assert_not_called()

    def test_annual_subscription_gets_yearly_allowance(self) -> None:
        now = self.service._now()
        sub = {"id": "sub_1", "status": "active", "customer_id": "cus_1", "recurring_interval": "year",
               "current_period_start": now.isoformat(), "current_period_end": (now + timedelta(days=365)).isoformat()}
        body = json.dumps({"type": "subscription.active", "data": {**sub, "metadata": {"devbareun_plan": "plus", "billing_cycle": "annual"}, "customer": {"email": "user@example.test"}}}).encode()
        inserted = []
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": self.SECRET}), \
                patch.object(self.service, "is_configured", return_value=True), \
                patch.object(self.service, "select_one", return_value=None), \
                patch.object(self.service, "insert_row", side_effect=lambda table, payload: inserted.append((table, payload)) or payload), \
                patch.object(self.service, "first_update", return_value={}), \
                patch.object(self.service, "call_rpc", return_value={"claimed": True}):
            result = self.service.handle_webhook(body, self.signed_headers(body))
        self.assertEqual(result["outcome"], "subscription_active")
        rows = [payload for table, payload in inserted if table == "subscriptions"]
        self.assertEqual(rows[0]["monthly_project_limit"], 60)
        self.assertEqual(rows[0]["provider"], "polar")

    def test_revoked_subscription_ends_access(self) -> None:
        self.assertEqual(self.service._subscription_status({"status": "active"}, "subscription.revoked"), "canceled")
        self.assertEqual(self.service._subscription_status({"status": "active", "cancel_at_period_end": True}, "subscription.canceled"), "active")
        self.assertEqual(self.service._subscription_status({"status": "past_due"}, "subscription.past_due"), "past_due")

    def test_unknown_product_is_ignored(self) -> None:
        body = json.dumps({"type": "order.paid", "data": {"id": "o", "metadata": {}, "product": {"metadata": {}}, "customer": {"email": "a@b.c"}}}).encode()
        with patch.dict(os.environ, {"POLAR_WEBHOOK_SECRET": self.SECRET}):
            result = self.service.handle_webhook(body, self.signed_headers(body))
        self.assertEqual(result["status"], "ignored")

    def test_checkout_status_pending_before_webhook(self) -> None:
        with patch.object(self.service, "is_configured", return_value=True), patch.object(self.service, "select_one", return_value=None):
            response = self.service.get_checkout_status(self.user(), "polar_checkout_unknown")
        self.assertEqual(response["checkout"]["status"], "payment_pending")

    def test_billing_contract_checker_passes(self) -> None:
        checker = importlib.import_module("check_billing_lifecycle")
        result = checker.check(ROOT)
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
