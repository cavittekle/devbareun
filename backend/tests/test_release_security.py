from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - local environments may not have backend deps installed.
    TestClient = None

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class ReleaseSecurityTests(unittest.TestCase):
    def test_legacy_project_routes_are_gone_by_default(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "true"
        os.environ["DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES"] = "false"
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        response = client.post("/api/projects/demo/preflight", json={})

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["code"], "legacy_route_disabled")

    def test_frontend_csp_disallows_inline_scripts(self) -> None:
        config_path = Path(__file__).resolve().parents[2] / "frontend" / "vercel.json"
        headers = json.loads(config_path.read_text(encoding="utf-8"))["headers"][0]["headers"]
        csp = next(item["value"] for item in headers if item["key"].lower() == "content-security-policy")

        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)


if __name__ == "__main__":
    unittest.main()
