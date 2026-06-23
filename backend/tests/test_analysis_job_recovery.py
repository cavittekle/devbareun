from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class AnalysisJobRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = importlib.import_module("app.services.analysis_job_service")
        cls.CurrentUser = importlib.import_module("app.auth_dependencies").CurrentUser

    def staff(self):
        return self.CurrentUser(
            id="operator-id",
            auth_user_id="operator-id",
            email="operator@devbareun.test",
            role="operator",
            is_admin=False,
        )

    def test_max_attempts_config_is_bounded(self) -> None:
        previous = os.environ.get("DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS")
        try:
            os.environ["DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS"] = "0"
            self.assertEqual(self.service.analysis_job_max_attempts(), 1)
            os.environ["DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS"] = "99"
            self.assertEqual(self.service.analysis_job_max_attempts(), 10)
            os.environ["DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS"] = "bad"
            self.assertEqual(self.service.analysis_job_max_attempts(), 3)
        finally:
            if previous is None:
                os.environ.pop("DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS", None)
            else:
                os.environ["DEVBAREUN_ANALYSIS_JOB_MAX_ATTEMPTS"] = previous

    def test_stale_exhausted_job_is_dead_lettered(self) -> None:
        stale = {
            "id": "job-stale",
            "status": "running",
            "attempts": 3,
            "max_attempts": 3,
            "last_heartbeat_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        }
        updates = []
        with patch.object(self.service, "_list_running_jobs", return_value=[stale]), patch.object(
            self.service, "_analysis_result_exists_for_job", return_value=False
        ), patch.object(self.service, "_update_job", side_effect=lambda job_id, payload: updates.append((job_id, payload))):
            count = self.service.requeue_stale_analysis_jobs(stale_after_minutes=5)

        self.assertEqual(count, 1)
        self.assertEqual(updates[0][0], "job-stale")
        self.assertEqual(updates[0][1]["status"], "dead_lettered")
        self.assertEqual(updates[0][1]["terminal_reason"], "worker_timeout_max_attempts")

    def test_stale_job_with_saved_result_is_completed_not_requeued(self) -> None:
        stale = {
            "id": "job-result",
            "status": "running",
            "attempts": 1,
            "max_attempts": 3,
            "last_heartbeat_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        }
        updates = []
        with patch.object(self.service, "_list_running_jobs", return_value=[stale]), patch.object(
            self.service, "_analysis_result_exists_for_job", return_value=True
        ), patch.object(self.service, "_update_job", side_effect=lambda job_id, payload: updates.append((job_id, payload))):
            self.service.requeue_stale_analysis_jobs(stale_after_minutes=5)

        self.assertEqual(updates[0][1]["status"], "completed")
        self.assertEqual(updates[0][1]["terminal_reason"], "result_recovered_after_worker_timeout")

    def test_dead_letter_retry_requires_explicit_reset(self) -> None:
        job = {
            "id": "job-dead",
            "status": "dead_lettered",
            "attempts": 3,
            "max_attempts": 3,
            "requeue_count": 2,
            "user_payload": {"id": "user", "auth_user_id": "user", "email": "user@example.test"},
        }
        with patch.object(self.service, "_find_job", return_value=job), patch.object(
            self.service, "_analysis_result_exists_for_job", return_value=False
        ):
            with self.assertRaises(HTTPException) as raised:
                self.service.requeue_analysis_job(job_id="job-dead", actor=self.staff(), reset_attempts=False)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["error"], "attempt_budget_exhausted")

        updates = []
        with patch.object(self.service, "_find_job", return_value=job), patch.object(
            self.service, "_analysis_result_exists_for_job", return_value=False
        ), patch.object(self.service, "_update_job", side_effect=lambda job_id, payload: updates.append((job_id, payload))):
            response = self.service.requeue_analysis_job(job_id="job-dead", actor=self.staff(), reset_attempts=True)

        self.assertEqual(response["status"], "queued")
        self.assertTrue(response["reset_attempts"])
        self.assertEqual(updates[0][1]["attempts"], 0)
        self.assertEqual(updates[0][1]["status"], "queued")

    def test_retry_refuses_job_with_persisted_result(self) -> None:
        job = {
            "id": "job-saved-result",
            "status": "failed",
            "attempts": 1,
            "max_attempts": 3,
            "user_payload": {"id": "user", "auth_user_id": "user", "email": "user@example.test"},
        }
        with patch.object(self.service, "_find_job", return_value=job), patch.object(
            self.service, "_analysis_result_exists_for_job", return_value=True
        ):
            with self.assertRaises(HTTPException) as raised:
                self.service.requeue_analysis_job(job_id="job-saved-result", actor=self.staff())
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["error"], "result_already_persisted")

    def test_recovery_surface_is_migrated_and_documented(self) -> None:
        migration = ROOT / "database" / "2026_06_19_v1417_analysis_job_recovery.sql"
        deploy_order = (ROOT / "database" / "SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
        routes = (ROOT / "backend" / "app" / "analysis_routes.py").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "ANALYSIS_JOB_RECOVERY_V1417.md").read_text(encoding="utf-8")

        self.assertIn(migration.name, deploy_order)
        self.assertIn("dead_lettered", migration.read_text(encoding="utf-8"))
        self.assertIn('@router.get("/operations/recovery-jobs")', routes)
        self.assertIn('@router.post("/operations/jobs/{job_id}/retry")', routes)
        self.assertIn("reset_attempts", docs)


if __name__ == "__main__":
    unittest.main()
