from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class AnalysisWorkerOperationsTests(unittest.TestCase):
    def test_observability_migration_is_ordered_and_protects_direct_access(self) -> None:
        migration = ROOT / "database" / "2026_06_19_v1416_analysis_worker_observability.sql"
        deploy_order = (ROOT / "database" / "SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
        sql = migration.read_text(encoding="utf-8")

        self.assertIn(migration.name, deploy_order)
        self.assertIn("analysis_worker_heartbeats", sql)
        self.assertIn("enable row level security", sql.lower())
        self.assertIn("for select", sql.lower())
        self.assertIn("using (false)", sql.lower())

    def test_worker_service_has_long_job_heartbeat_and_safe_operations_summary(self) -> None:
        service = (ROOT / "backend" / "app" / "services" / "analysis_job_service.py").read_text(encoding="utf-8")
        worker = (ROOT / "backend" / "app" / "analysis_worker.py").read_text(encoding="utf-8")
        route = (ROOT / "backend" / "app" / "analysis_routes.py").read_text(encoding="utf-8")

        self.assertIn("class _JobHeartbeat", service)
        self.assertIn("heartbeat_analysis_job", service)
        self.assertIn("record_analysis_worker_heartbeat", service)
        self.assertIn("analysis_operations_status", service)
        self.assertIn('status="degraded"', worker)
        self.assertIn('status="stopped"', worker)
        self.assertIn('@router.get("/operations")', route)
        self.assertIn('require_staff_permission(current_user, "operations")', route)

    def test_heartbeat_config_is_bounded(self) -> None:
        service = importlib.import_module("app.services.analysis_job_service")
        prior = os.environ.get("DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS")
        try:
            os.environ["DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS"] = "1"
            self.assertEqual(service.analysis_job_heartbeat_interval_seconds(), 10)
            os.environ["DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS"] = "9999"
            self.assertEqual(service.analysis_job_heartbeat_interval_seconds(), 600)
        finally:
            if prior is None:
                os.environ.pop("DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS", None)
            else:
                os.environ["DEVBAREUN_ANALYSIS_JOB_HEARTBEAT_SECONDS"] = prior

    def test_operations_route_is_part_of_openapi_and_staff_guarded(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        module = importlib.import_module("app.main")
        client = TestClient(module.app)
        spec = client.get("/openapi.json").json()
        self.assertIn("/api/analysis/operations", spec["paths"])
