from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


class ErrorTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = dict(os.environ)
        os.environ["DEVBAREUN_RATE_LIMIT_ENABLED"] = "false"
        os.environ["DEVBAREUN_ERROR_TELEMETRY_MODE"] = "log"
        os.environ["DEVBAREUN_REQUIRE_ERROR_TELEMETRY"] = "false"
        os.environ.pop("DEVBAREUN_SENTRY_DSN", None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._original)

    def test_sanitize_metadata_redacts_nested_secrets(self) -> None:
        telemetry = importlib.import_module("app.telemetry")
        payload = telemetry.sanitize_metadata({
            "authorization": "Bearer top-secret-token",
            "details": {"api_key": "sk-super-secret", "safe": "ok"},
            "list": ["normal", "token=hidden"],
        })
        text = json.dumps(payload)
        self.assertIn("[REDACTED]", text)
        self.assertNotIn("top-secret-token", text)
        self.assertNotIn("sk-super-secret", text)
        self.assertNotIn("token=hidden", text)
        self.assertEqual(payload["details"]["safe"], "ok")

    def test_status_never_returns_sentry_dsn(self) -> None:
        os.environ["DEVBAREUN_ERROR_TELEMETRY_MODE"] = "sentry"
        os.environ["DEVBAREUN_SENTRY_DSN"] = "https://public@example.ingest.sentry.io/123"
        telemetry = importlib.import_module("app.telemetry")
        payload = telemetry.error_telemetry_status()
        rendered = json.dumps(payload)
        self.assertEqual(payload["mode"], "sentry")
        self.assertNotIn("example.ingest", rendered)
        self.assertNotIn("DEVBAREUN_SENTRY_DSN", rendered)

    def test_unhandled_error_returns_safe_request_id(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        app_module = importlib.import_module("app.main")
        route_path = "/__error-telemetry-test-boom"
        if not any(getattr(route, "path", None) == route_path for route in app_module.app.routes):
            @app_module.app.get(route_path)
            def _boom() -> None:
                raise RuntimeError("token=do-not-leak")
        client = TestClient(app_module.app, raise_server_exceptions=False)
        response = client.get(route_path)
        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["code"], "internal_error")
        self.assertTrue(payload.get("request_id"))
        self.assertEqual(response.headers.get("X-Request-ID"), payload["request_id"])
        self.assertNotIn("do-not-leak", response.text)

    def test_static_contract_and_release_assets_exist(self) -> None:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "tools"))
        checker = importlib.import_module("check_error_telemetry")
        result = checker.check(root)
        self.assertEqual(result.errors, [])
        self.assertIn("sentry-sdk", (root / "backend" / "requirements.txt").read_text(encoding="utf-8"))
        self.assertIn("v1.4.28", (root / "docs" / "CHANGELOG.md").read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
