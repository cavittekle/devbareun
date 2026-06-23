from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))


class ApiContractReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        os.environ["DEVBAREUN_EXPOSE_LEGACY_PROJECT_ROUTES"] = "false"
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "false"

    def test_api_contract_tool_passes_current_routes(self) -> None:
        export_api_contract = importlib.import_module("export_api_contract")

        result = export_api_contract.check_contract(ROOT)

        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_required_canonical_routes_exist_and_legacy_routes_stay_out_of_openapi(self) -> None:
        export_api_contract = importlib.import_module("export_api_contract")
        manifest = export_api_contract.route_manifest(ROOT)
        route_keys = {(route["method"], route["path"]) for route in manifest["routes"]}
        openapi_keys = {
            (route["method"], route["path"])
            for route in manifest["routes"]
            if route["include_in_schema"]
        }

        for method, path in export_api_contract.REQUIRED_ROUTES:
            self.assertIn((method, path), route_keys)
        for method, path in export_api_contract.LEGACY_PROJECT_ROUTES:
            self.assertIn((method, path), route_keys)
            self.assertNotIn((method, path), openapi_keys)

    def test_openapi_schema_contains_canonical_paths_only_for_legacy_project_family(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/projects/create", paths)
        self.assertIn("/api/uploads/create-url", paths)
        self.assertIn("/api/analysis/start/{project_id}", paths)
        self.assertNotIn("/api/projects/{project_id}/upload", paths)
        self.assertNotIn("/api/projects/{project_id}/analyze", paths)
        self.assertNotIn("/api/payments/create-checkout", paths)

    def test_react_workspace_has_no_deprecated_endpoint_references(self) -> None:
        export_api_contract = importlib.import_module("export_api_contract")

        errors = export_api_contract._scan_react_client(ROOT)

        self.assertEqual(errors, [])

    def test_auth_routes_no_longer_double_register_me_or_logout(self) -> None:
        export_api_contract = importlib.import_module("export_api_contract")
        manifest = export_api_contract.route_manifest(ROOT)
        occurrences = {}
        for route in manifest["routes"]:
            key = (route["method"], route["path"])
            occurrences.setdefault(key, []).append(route["name"])

        self.assertEqual(occurrences[("GET", "/api/auth/me")], ["auth_me"])
        self.assertEqual(occurrences[("POST", "/api/auth/logout")], ["logout"])


if __name__ == "__main__":
    unittest.main()
