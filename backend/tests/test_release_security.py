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
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
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

    def test_pilot_login_requires_explicit_local_flag(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "false"
        os.environ["DEVBAREUN_ENABLE_PILOT_LOGIN"] = "false"
        os.environ.pop("DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT", None)
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        response = client.post("/api/auth/pilot-login", json={"email": "test@example.com", "password": "demo"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "http_403")

    def test_staff_role_normalization_and_permissions(self) -> None:
        auth_dependencies = importlib.import_module("app.auth_dependencies")
        saas_routes = importlib.import_module("app.saas_routes")

        self.assertEqual(auth_dependencies.normalize_user_role("admin"), "owner")
        self.assertEqual(auth_dependencies.normalize_user_role("user"), "customer")
        self.assertEqual(auth_dependencies.normalize_user_role(None), "customer")
        self.assertTrue(saas_routes._can_access("owner", "staff"))
        self.assertFalse(saas_routes._can_access("support", "payments"))
        self.assertTrue(saas_routes._can_access("finance", "payments"))
        self.assertFalse(saas_routes._can_access("finance", "staff"))

    def test_version_endpoint_and_pilot_checkout_are_production_safe(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "true"
        os.environ["DEVBAREUN_ENABLE_PILOT_CHECKOUT"] = "false"
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        version = client.get("/api/version")
        self.assertEqual(version.status_code, 200)
        self.assertIn("version", version.json())
        self.assertTrue(version.json()["production_security"])

        response = client.post("/api/payments/activate-pilot-checkout?checkout_id=test")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "http_403")


    def test_cookie_auth_mutation_requires_origin_and_csrf_in_production(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "true"
        os.environ["DEVBAREUN_REQUIRE_CSRF_TOKEN"] = "true"
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        module = importlib.import_module("app.main")
        client = TestClient(module.app)
        client.cookies.set("devbareun_auth", "fake-session-token")

        missing_origin = client.post("/api/auth/logout")
        self.assertEqual(missing_origin.status_code, 403)
        self.assertEqual(missing_origin.json()["code"], "origin_required")

        missing_csrf = client.post("/api/auth/logout", headers={"Origin": "https://devbareun.com"})
        self.assertEqual(missing_csrf.status_code, 403)
        self.assertEqual(missing_csrf.json()["code"], "csrf_failed")

        client.cookies.set("devbareun_csrf", "csrf-token")
        allowed = client.post(
            "/api/auth/logout",
            headers={"Origin": "https://devbareun.com", "X-CSRF-Token": "csrf-token"},
        )
        self.assertEqual(allowed.status_code, 200)

    def test_static_frontend_does_not_allow_production_local_token_override(self) -> None:
        api_path = Path(__file__).resolve().parents[2] / "frontend" / "js" / "devbareun-api.js"
        source = api_path.read_text(encoding="utf-8")

        self.assertNotIn("devbareun_allow_local_token_storage", source)
        self.assertIn("X-CSRF-Token", source)

    def test_production_rate_limit_requires_redis_or_explicit_override(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "true"
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "false"
        os.environ["DEVBAREUN_RATE_LIMIT_ENABLED"] = "true"
        os.environ.pop("UPSTASH_REDIS_REST_URL", None)
        os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        response = client.get("/api/saas/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "rate_limiter_not_configured")


class AnalysisWorkerReleaseTests(unittest.TestCase):
    def test_analysis_worker_cli_and_job_modes_are_present(self) -> None:
        service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "analysis_job_service.py"
        worker_path = Path(__file__).resolve().parents[1] / "app" / "analysis_worker.py"
        service_source = service_path.read_text(encoding="utf-8")
        worker_source = worker_path.read_text(encoding="utf-8")

        self.assertIn("DEVBAREUN_ANALYSIS_JOB_MODE", service_source)
        self.assertIn('"worker"', service_source)
        self.assertIn("run_worker_once", service_source)
        self.assertIn("requeue_stale_analysis_jobs", service_source)
        self.assertIn("python -m app.analysis_worker", (Path(__file__).resolve().parents[2] / "docs" / "ANALYSIS_WORKER_V145.md").read_text(encoding="utf-8"))
        self.assertIn("argparse", worker_source)
        self.assertIn("--loop", worker_source)

    def test_analysis_worker_migration_is_in_deploy_order(self) -> None:
        root = Path(__file__).resolve().parents[2]
        migration = root / "database" / "2026_06_18_v145_analysis_worker.sql"
        deploy_order = (root / "database" / "SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
        sql = migration.read_text(encoding="utf-8")

        self.assertIn("2026_06_18_v145_analysis_worker.sql", deploy_order)
        self.assertIn("worker_id", sql)
        self.assertIn("last_heartbeat_at", sql)
        self.assertIn("attempts", sql)
        self.assertIn("user_payload", sql)


if __name__ == "__main__":
    unittest.main()


class ProductionReadinessReleaseTests(unittest.TestCase):
    def test_readiness_endpoint_exposes_secret_safe_release_flags(self) -> None:
        if TestClient is None:
            self.skipTest("FastAPI test dependencies are not installed.")
        os.environ["DEVBAREUN_ENV"] = "production"
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "true"
        os.environ["DEVBAREUN_REQUIRE_CSRF_TOKEN"] = "true"
        os.environ["DEVBAREUN_ANALYSIS_JOB_MODE"] = "worker"
        os.environ["DEVBAREUN_ENABLE_DEV_AUTH"] = "false"
        os.environ["DEVBAREUN_ENABLE_LOCAL_STORE"] = "false"
        os.environ["DEVBAREUN_ENABLE_MOCK_PAYMENT"] = "false"
        os.environ["DEVBAREUN_ENABLE_PILOT_LOGIN"] = "false"
        os.environ["DEVBAREUN_ENABLE_PILOT_CHECKOUT"] = "false"
        os.environ["DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD"] = "false"
        os.environ["DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES"] = "false"
        os.environ["DEVBAREUN_DISABLE_DOCS"] = "true"
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        module = importlib.import_module("app.main")
        client = TestClient(module.app)

        response = client.get("/api/readiness")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ready", payload)
        self.assertIn("errors", payload)
        self.assertIn("warnings", payload)
        self.assertEqual(payload["readiness"]["csrf_token"], "required")
        self.assertEqual(payload["readiness"]["analysis_job_mode"], "worker")
        self.assertNotIn("SERVICE_ROLE", json.dumps(payload).upper())

    def test_cross_platform_readiness_tools_are_present(self) -> None:
        root = Path(__file__).resolve().parents[2]
        validate_path = root / "tools" / "validate_production_env.py"
        smoke_path = root / "tools" / "smoke_deploy.py"
        validate_source = validate_path.read_text(encoding="utf-8")
        smoke_source = smoke_path.read_text(encoding="utf-8")

        self.assertIn("BACKEND_REQUIRED", validate_source)
        self.assertIn("FRONTEND_FORBIDDEN", validate_source)
        self.assertIn("DEVBAREUN_ANALYSIS_JOB_MODE", validate_source)
        self.assertIn("api/readiness", smoke_source)
        self.assertIn("csrf initializer", smoke_source)
        self.assertIn("urllib.request", smoke_source)


class ReleaseGatePackagingTests(unittest.TestCase):
    def test_release_gate_and_package_tools_are_present_and_cross_platform(self) -> None:
        root = Path(__file__).resolve().parents[2]
        release_gate = root / "tools" / "release_gate.py"
        package_release = root / "tools" / "package_release.py"
        gate_source = release_gate.read_text(encoding="utf-8")
        package_source = package_release.read_text(encoding="utf-8")
        ci_source = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("FORBIDDEN_DIR_NAMES", gate_source)
        self.assertIn("SECRET_PATTERNS", gate_source)
        self.assertIn("SUPABASE_DEPLOY_ORDER.md", gate_source)
        self.assertIn("tools/release_gate.py", ci_source)
        self.assertIn("tools/validate_production_env.py", ci_source)
        self.assertIn("tools/export_api_contract.py", ci_source)
        self.assertIn("npm ci", ci_source)
        self.assertIn("EXCLUDED_DIRS", package_source)
        self.assertIn("devbareun_full_v1.4.0_latest", package_source)
        self.assertIn("sha256", package_source)

    def test_release_gate_accepts_current_source_tree(self) -> None:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "tools"))
        release_gate = importlib.import_module("release_gate")

        result = release_gate.run(root)

        self.assertEqual(result.errors, [])
        self.assertIn("1.4.10", (root / "docs" / "CHANGELOG.md").read_text(encoding="utf-8"))
