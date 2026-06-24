from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class AnalysisIdempotencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = importlib.import_module("app.services.analysis_job_service")
        cls.CurrentUser = importlib.import_module("app.auth_dependencies").CurrentUser

    def user(self):
        return self.CurrentUser(id="user-id", auth_user_id="user-id", email="user@example.test", role="member")

    def project(self):
        return {"id": "project-id", "project_id": "project-id", "owner_email": "user@example.test"}

    def test_same_idempotency_key_replays_existing_job(self) -> None:
        existing = {"id": "job-existing", "status": "queued", "idempotency_key": "key-123", "request_fingerprint": self.service._analysis_request_fingerprint("project-id", self.service.normalize_analysis_type("all"))}
        with patch.object(self.service, "_find_idempotent_job", return_value=existing), patch.object(self.service, "_find_active_job_for_project", return_value=None):
            response = self.service.create_analysis_job(project_id="project-id", project=self.project(), user=self.user(), background_tasks=BackgroundTasks(), idempotency_key="key-123")
        self.assertEqual(response["job_id"], "job-existing")
        self.assertTrue(response["idempotent_replay"])

    def test_key_reuse_for_different_request_is_rejected(self) -> None:
        existing = {"id": "job-existing", "status": "queued", "idempotency_key": "key-123", "request_fingerprint": "other"}
        with patch.object(self.service, "_find_idempotent_job", return_value=existing), patch.object(self.service, "_find_active_job_for_project", return_value=None):
            with self.assertRaises(HTTPException) as raised:
                self.service.create_analysis_job(project_id="project-id", project=self.project(), user=self.user(), background_tasks=BackgroundTasks(), idempotency_key="key-123")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["error"], "idempotency_key_reused")

    def test_active_job_is_reused_without_key(self) -> None:
        active = {"id": "job-active", "status": "running"}
        with patch.object(self.service, "_find_idempotent_job", return_value=None), patch.object(self.service, "_find_active_job_for_project", return_value=active):
            response = self.service.create_analysis_job(project_id="project-id", project=self.project(), user=self.user(), background_tasks=BackgroundTasks())
        self.assertEqual(response["job_id"], "job-active")
        self.assertTrue(response["active_job_reused"])

    def test_atomic_usage_rpc_is_used_for_configured_uuid_jobs(self) -> None:
        billing = importlib.import_module("app.services.billing_service")
        job_id = "11111111-1111-1111-1111-111111111111"
        with patch.object(billing, "is_configured", return_value=True), patch.object(billing, "call_rpc", return_value={"consumed": True, "already_consumed": False, "mode": "credit", "ledger_id": "ledger"}), patch.object(billing, "_log_activity") as log:
            result = billing.consume_after_success(self.user(), "project-id", job_id)
        self.assertTrue(result["consumed"])
        log.assert_called_once()

    def test_idempotency_surface_is_migrated_and_documented(self) -> None:
        migration = ROOT / "database" / "2026_06_19_v1418_analysis_idempotency.sql"
        docs = ROOT / "docs" / "ANALYSIS_IDEMPOTENCY_V1418.md"
        deploy_order = (ROOT / "database" / "SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
        self.assertIn(migration.name, deploy_order)
        source = migration.read_text(encoding="utf-8")
        self.assertIn("analysis_usage_ledger", source)
        self.assertIn("consume_analysis_usage_once", source)
        self.assertIn("Idempotency-Key", docs.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
