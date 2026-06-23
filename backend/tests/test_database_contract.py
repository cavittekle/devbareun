from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


class DatabaseContractTests(unittest.TestCase):
    def test_database_contract_tool_passes_current_migrations(self) -> None:
        check_database_contract = importlib.import_module("check_database_contract")

        result = check_database_contract.check_contract(ROOT)

        self.assertEqual(result.errors, [])
        self.assertIn("2026_06_19_v1419_report_snapshot_integrity.sql", result.contract.deploy_order)

    def test_core_backend_tables_have_contract_columns(self) -> None:
        check_database_contract = importlib.import_module("check_database_contract")
        result = check_database_contract.check_contract(ROOT)
        tables = result.contract.tables

        self.assertTrue({"project_id", "owner_email", "project_status", "analysis_type"}.issubset(tables["projects"]))
        self.assertTrue({"storage_bucket", "storage_path", "original_name", "file_size_bytes", "status"}.issubset(tables["uploaded_files"]))
        self.assertTrue({"worker_id", "locked_at", "last_heartbeat_at", "attempts", "user_payload"}.issubset(tables["analysis_jobs"]))
        self.assertTrue({"result_json", "dashboard", "kpis", "report_payload", "owner_email"}.issubset(tables["analysis_results"]))
        self.assertTrue({"remaining", "remaining_credits", "used_credits", "total_credits"}.issubset(tables["analysis_credits"]))
        self.assertTrue({"report_payload", "payload_sha256", "content_sha256", "snapshot_version", "generated_at", "last_downloaded_at"}.issubset(tables["reports"]))
        self.assertTrue({"archive_id", "audit_id", "event_hash", "payload_sha256", "lease_token", "status"}.issubset(tables["audit_archive_outbox"]))

    def test_rls_and_storage_contract_are_present(self) -> None:
        check_database_contract = importlib.import_module("check_database_contract")
        result = check_database_contract.check_contract(ROOT)

        for table in ("projects", "uploaded_files", "analysis_jobs", "analysis_results", "reports", "payments"):
            self.assertIn(table, result.contract.rls_enabled)
            self.assertIn(table, result.contract.policy_tables)
        self.assertGreaterEqual(result.contract.storage_policy_count, 3)
        self.assertEqual(result.contract.storage_buckets.get("project-files"), False)

    def test_release_gate_and_ci_call_database_contract_checker(self) -> None:
        gate_source = (ROOT / "tools" / "release_gate.py").read_text(encoding="utf-8")
        ci_source = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("tools/check_database_contract.py", gate_source)
        self.assertIn("2026_06_19_v1413_database_contract_bridge.sql", gate_source)
        self.assertIn("tools/check_database_contract.py", ci_source)


if __name__ == "__main__":
    unittest.main()
