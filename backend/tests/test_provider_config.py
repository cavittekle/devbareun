from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


class ProviderConfigTests(unittest.TestCase):
    def test_provider_templates_pass_shape_check(self) -> None:
        checker = importlib.import_module("check_provider_config")
        validator = importlib.import_module("validate_production_env")

        result = checker.check_provider_config(
            validator.parse_env(ROOT / "deploy/env/railway-web.env.template"),
            validator.parse_env(ROOT / "deploy/env/railway-worker.env.template"),
            validator.parse_env(ROOT / "deploy/env/vercel.env.template"),
            railway_audit_archive=validator.parse_env(ROOT / "deploy/env/railway-audit-archive.env.template"),
            allow_placeholders=True,
        )

        self.assertEqual(result.errors, [])
        self.assertGreater(len(result.warnings), 0)

    def test_provider_config_detects_worker_drift_without_exposing_values(self) -> None:
        checker = importlib.import_module("check_provider_config")
        validator = importlib.import_module("validate_production_env")
        web = validator.parse_env(ROOT / "deploy/env/railway-web.env.template")
        worker = dict(web)
        frontend = validator.parse_env(ROOT / "deploy/env/vercel.env.template")
        worker["SUPABASE_URL"] = "https://different-project.supabase.co"

        result = checker.check_provider_config(web, worker, frontend, allow_placeholders=True)

        self.assertTrue(any("configuration drift: SUPABASE_URL" in error for error in result.errors))
        self.assertNotIn("different-project.supabase.co", "\n".join(result.errors))

    def test_release_gate_ci_and_runbook_reference_provider_preflight(self) -> None:
        gate = (ROOT / "tools/release_gate.py").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        runbook = (ROOT / "docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md").read_text(encoding="utf-8")
        preflight = (ROOT / "docs/PRODUCTION_CONFIG_PREFLIGHT_V1415.md").read_text(encoding="utf-8")

        self.assertIn("tools/check_provider_config.py", gate)
        self.assertIn("tools/check_provider_config.py", ci)
        self.assertIn("tools/check_provider_config.py", runbook)
        self.assertIn("configuration drift", preflight.lower())
        for template in (
            "deploy/env/railway-web.env.template",
            "deploy/env/railway-worker.env.template",
            "deploy/env/railway-audit-archive.env.template",
            "deploy/env/vercel.env.template",
        ):
            self.assertTrue((ROOT / template).exists())


if __name__ == "__main__":
    unittest.main()
