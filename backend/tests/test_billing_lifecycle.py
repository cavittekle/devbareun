from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

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

    def test_append_checkout_id_preserves_existing_return_query(self) -> None:
        url = self.service._append_checkout_id(
            "https://devbareun.com/workspace/?view=payment-success&plan=plus",
            "checkout-abc",
        )
        self.assertIn("view=payment-success", url)
        self.assertIn("plan=plus", url)
        self.assertIn("checkout_id=checkout-abc", url)

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

    def test_subscription_usage_resets_only_when_provider_period_advances(self) -> None:
        prior_end = self.service._now() + timedelta(days=2)
        new_end = prior_end + timedelta(days=30)
        existing = {
            "id": "sub-1",
            "used_project_count": 4,
            "current_period_start": (prior_end - timedelta(days=30)).isoformat(),
            "current_period_end": prior_end.isoformat(),
        }
        obj = {"id": "provider-sub-1", "customer": "customer-1", "attributes": {"renews_at": new_end.isoformat(), "created_at": prior_end.isoformat()}}
        with patch.object(self.service, "is_configured", return_value=True), patch.object(self.service, "select_one", return_value=existing), patch.object(self.service, "first_update", side_effect=lambda _table, _filters, payload: payload) as update:
            result = self.service._upsert_subscription(self.user().id, self.user().email, "plus", obj, "active")
        self.assertEqual(result["used_project_count"], 0)
        self.assertEqual(update.call_args.args[0], "subscriptions")

    def test_checkout_record_keeps_text_project_id(self) -> None:
        captured = {}
        def capture(_table, payload):
            captured.update(payload)
            return payload
        with patch.object(self.service, "is_configured", return_value=True), patch.object(self.service, "insert_row", side_effect=capture):
            self.service._record_checkout_session(
                self.user(),
                checkout_id="checkout-1",
                plan="single",
                project_id="legacy-project-public-id",
                provider_session_id="lemon-1",
                checkout_url="https://checkout.example.test/1",
            )
        self.assertEqual(captured["project_id"], "legacy-project-public-id")

    def test_webhook_claim_uses_redacted_event_owner(self) -> None:
        event = {
            "meta": {
                "event_id": "evt-001",
                "event_name": "order_created",
                "custom_data": {"checkout_id": "checkout-1", "plan": "single", "email": "private@example.test", "project_id": "none"},
            },
            "data": {"id": "order-1", "attributes": {}},
        }
        with patch.object(self.service, "production_security_enabled", return_value=False), patch.object(self.service, "_claim_payment_event", return_value={"claimed": True, "state": "processing"}) as claim, patch.object(self.service, "_process_lemon_event", return_value={"outcome": "credit_granted"}), patch.object(self.service, "_complete_payment_event"):
            response = self.service._handle_lemon_webhook(json.dumps(event).encode("utf-8"), None)
        self.assertEqual(response["status"], "handled")
        self.assertNotIn("p_owner_email", claim.call_args.kwargs)
        summary = claim.call_args.args[2]
        self.assertNotIn("private@example.test", json.dumps(summary))
        self.assertIn("owner_email_sha256", summary)

    def test_signed_webhook_uses_server_checkout_context(self) -> None:
        event = {
            "meta": {
                "event_id": "evt-context",
                "event_name": "order_created",
                "custom_data": {"checkout_id": "checkout-context", "plan": "single", "email": "untrusted@example.test", "project_id": "untrusted-project"},
            },
            "data": {"id": "order-context", "attributes": {}},
        }
        context = {"owner_email": "owner@example.test", "user_id": "owner-user", "project_id": "server-project", "plan": "single"}
        with patch.object(self.service, "production_security_enabled", return_value=False), patch.object(self.service, "_checkout_owner_context", return_value=context), patch.object(self.service, "_claim_payment_event", return_value={"claimed": True, "state": "processing"}), patch.object(self.service, "_process_lemon_event", return_value={"outcome": "credit_granted"}) as process, patch.object(self.service, "_complete_payment_event"):
            self.service._handle_lemon_webhook(json.dumps(event).encode("utf-8"), None)
        self.assertEqual(process.call_args.kwargs["email"], "owner@example.test")
        self.assertEqual(process.call_args.kwargs["user_id"], "owner-user")
        self.assertEqual(process.call_args.kwargs["project_id"], "server-project")

    def test_duplicate_webhook_does_not_reapply_side_effects(self) -> None:
        event = {
            "meta": {"event_id": "evt-duplicate", "event_name": "order_created", "custom_data": {"plan": "single"}},
            "data": {"id": "order-duplicate", "attributes": {}},
        }
        with patch.object(self.service, "production_security_enabled", return_value=False), patch.object(self.service, "_claim_payment_event", return_value={"claimed": False, "state": "duplicate_processed"}), patch.object(self.service, "_process_lemon_event") as process:
            response = self.service._handle_lemon_webhook(json.dumps(event).encode("utf-8"), None)
        self.assertEqual(response["status"], "duplicate_ignored")
        process.assert_not_called()

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

    def test_lemon_checkout_returns_correlation_id_and_persists_it(self) -> None:
        checkout_id = UUID("22222222-2222-2222-2222-222222222222")
        provider_response = {"data": {"id": "lemon-checkout-1", "attributes": {"url": "https://checkout.lemonsqueezy.com/one"}}}
        with patch.dict(os.environ, {
            "LEMON_SQUEEZY_SINGLE_VARIANT_ID": "123",
            "LEMON_SQUEEZY_STORE_ID": "456",
            "LEMON_SQUEEZY_API_KEY": "test-token",
        }, clear=False), patch.object(self.service, "uuid4", return_value=checkout_id), patch.object(self.service, "_lemon_post", return_value=provider_response) as lemon, patch.object(self.service, "_record_checkout_session") as save_checkout, patch.object(self.service, "_insert_payment") as save_payment:
            response = self.service._create_lemon_checkout(
                user=self.user(),
                plan="single",
                mode="payment",
                project_id="project-text-id",
                success_url="https://devbareun.com/workspace/?view=payment-success",
                cancel_url="https://devbareun.com/workspace/?view=payment-failed",
            )
        self.assertEqual(response["checkout_id"], str(checkout_id))
        payload = lemon.call_args.args[1]
        self.assertEqual(payload["data"]["attributes"]["checkout_data"]["custom"]["checkout_id"], str(checkout_id))
        self.assertIn(f"checkout_id={checkout_id}", payload["data"]["attributes"]["product_options"]["redirect_url"])
        save_checkout.assert_called_once()
        save_payment.assert_called_once()

    def test_billing_contract_checker_passes(self) -> None:
        checker = importlib.import_module("check_billing_lifecycle")
        result = checker.check(ROOT)
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
