from __future__ import annotations

import hashlib
import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class ReportSnapshotIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = importlib.import_module("app.services.report_service")
        cls.CurrentUser = importlib.import_module("app.auth_dependencies").CurrentUser

    def user(self):
        return self.CurrentUser(id="user-id", auth_user_id="user-id", email="user@example.test", role="customer")

    def project(self):
        return {"id": "project-id", "project_id": "project-id", "project_name": "Tower A", "owner_email": "user@example.test"}

    def analysis_result(self):
        return {
            "id": "analysis-id",
            "project_id": "project-id",
            "created_at": "2026-06-19T12:00:00Z",
            "confidence_score": 87,
            "dashboard_data": {"project": {"name": "Tower A", "currency": "AZN"}, "metrics": {"planned_progress": 40}},
            "risk_data": [],
        }

    def test_generate_persists_frozen_payload_and_checksums(self) -> None:
        captured = {}

        def capture_insert(**kwargs):
            captured.update(kwargs)
            return {"id": "report-id", "report_id": "report-id", **kwargs}

        with patch.object(self.service, "get_latest_analysis_result", return_value=self.analysis_result()), \
             patch.object(self.service, "build_pdf_bytes", return_value=b"pdf-bytes"), \
             patch.object(self.service, "local_store_enabled", return_value=False), \
             patch.object(self.service, "_insert_report_row", side_effect=capture_insert):
            response = self.service.generate_report("project-id", self.project(), self.user(), "pdf", "Project Control Report")

        self.assertTrue(response["download_ready"])
        self.assertEqual(captured["report_payload"]["dashboard"]["project"]["name"], "Tower A")
        self.assertEqual(captured["payload_sha256"], self.service._payload_sha256(captured["report_payload"]))
        self.assertEqual(captured["content_sha256"], hashlib.sha256(b"pdf-bytes").hexdigest())
        self.assertTrue(response["report"]["snapshot_available"])

    def test_download_uses_report_snapshot_before_latest_result(self) -> None:
        report = {
            "id": "report-id",
            "owner_email": "user@example.test",
            "format": "PDF",
            "report_name": "Tower A Project Control Report",
            "report_payload": {"dashboard": {"project": {"name": "Frozen Tower"}}},
        }
        with patch.object(self.service, "_find_report", return_value=report), \
             patch.object(self.service, "build_pdf_bytes", return_value=b"frozen-pdf") as build, \
             patch.object(self.service, "_find_result_for_report") as latest, \
             patch.object(self.service, "_record_report_download") as audit:
            content, media_type, filename = self.service.get_report_download("report-id", self.user())

        self.assertEqual(content, b"frozen-pdf")
        self.assertEqual(media_type, "application/pdf")
        self.assertTrue(filename.endswith(".pdf"))
        build.assert_called_once_with(report["report_payload"], lang="en", paper="a4")
        latest.assert_not_called()
        audit.assert_called_once()

    def test_invalid_report_format_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            self.service.normalize_report_format("docx")
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["error"], "unsupported_report_format")

    def test_download_audit_uses_atomic_rpc_for_production_uuid_row(self) -> None:
        report = {"id": "11111111-1111-1111-1111-111111111111", "owner_email": "user@example.test"}
        with patch.object(self.service, "is_configured", return_value=True), \
             patch.object(self.service, "call_rpc", return_value={"download_count": 1}) as rpc:
            self.service._record_report_download(report, self.user())
        rpc.assert_called_once_with("record_report_download", {"p_report_id": report["id"]})

    def test_snapshot_contract_is_migrated_and_documented(self) -> None:
        migration = ROOT / "database" / "2026_06_19_v1419_report_snapshot_integrity.sql"
        docs = ROOT / "docs" / "REPORT_SNAPSHOT_INTEGRITY_V1419.md"
        deploy_order = (ROOT / "database" / "SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
        self.assertIn(migration.name, deploy_order)
        source = migration.read_text(encoding="utf-8")
        self.assertIn("record_report_download", source)
        self.assertIn("payload_sha256", source)
        self.assertIn("legacy", docs.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
