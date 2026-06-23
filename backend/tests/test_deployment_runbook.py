from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


class DeploymentRunbookTests(unittest.TestCase):
    def test_deployment_runbook_contract_passes(self) -> None:
        check_deploy_runbook = importlib.import_module("check_deploy_runbook")

        result = check_deploy_runbook.check_contract(ROOT)

        self.assertEqual(result.errors, [])
        self.assertIn("2026_06_19_v1419_report_snapshot_integrity.sql", result.deploy_order)

    def test_runbook_mentions_provider_order_and_smoke_test(self) -> None:
        runbook = (ROOT / "docs" / "PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md").read_text(encoding="utf-8")

        for expected in (
            "Supabase",
            "Railway web service",
            "Railway worker service",
            "Railway audit archive worker",
            "Vercel",
            "Lemon Squeezy",
            "python tools/smoke_deploy.py",
            "python -m app.analysis_worker --loop",
            "python -m app.audit_archive_worker --loop",
            "DEVBAREUN_ANALYSIS_JOB_MODE=worker",
            "Root Directory = backend",
            "Root Directory = frontend",
        ):
            self.assertIn(expected, runbook)

    def test_env_matrix_marks_private_values_backend_only(self) -> None:
        matrix = (ROOT / "docs" / "DEPLOYMENT_ENV_MATRIX_V1414.md").read_text(encoding="utf-8")

        for secret in (
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_JWT_SECRET",
            "LEMON_SQUEEZY_API_KEY",
            "LEMON_SQUEEZY_WEBHOOK_SECRET",
            "UPSTASH_REDIS_REST_TOKEN",
            "DATABASE_URL",
            "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_URL",
            "DEVBAREUN_AUDIT_ARCHIVE_WEBHOOK_SECRET",
        ):
            self.assertIn(f"`{secret}` | Backend only", matrix)

    def test_release_gate_and_ci_call_deployment_runbook_checker(self) -> None:
        gate_source = (ROOT / "tools" / "release_gate.py").read_text(encoding="utf-8")
        ci_source = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("tools/check_deploy_runbook.py", gate_source)
        self.assertIn("docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md", gate_source)
        self.assertIn("tools/check_deploy_runbook.py", ci_source)


if __name__ == "__main__":
    unittest.main()
