from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.auth_dependencies import CurrentUser
from app.operations_routes import get_operations_health
from app.saas_admin_routes import admin_operations_health
from app.services.operations_health_service import operations_health_status


def _component(result: dict, name: str) -> dict:
    return next(item for item in result["components"] if item["name"] == name)


def test_operations_health_aggregates_worker_and_archive_incidents_without_payloads() -> None:
    with patch("app.services.operations_health_service.runtime_readiness_report", return_value={"ready": True, "errors": [], "warnings": [], "readiness": {"environment": "production"}}), \
         patch("app.services.operations_health_service.analysis_operations_status", return_value={"store": "supabase", "execution_mode": "worker", "worker_required": True, "worker_available": False, "healthy_worker_count": 0, "queue": {"queued": 2, "running": 0, "failed": 1, "dead_lettered": 1}}), \
         patch("app.services.operations_health_service.audit_archive_operations_status", return_value={"mode": "webhook", "available": True, "delivery_ready": True, "workers": [], "pending": 1, "dead_lettered": 1, "payload": {"must_not": "leak"}}):
        result = operations_health_status()

    assert result["status"] == "degraded"
    codes = {item["code"] for item in result["incidents"]}
    assert {"analysis_worker_unavailable", "analysis_failed_jobs", "analysis_dead_lettered_jobs", "audit_archive_worker_unavailable", "audit_archive_dead_lettered"}.issubset(codes)
    assert _component(result, "analysis")["summary"]["queued"] == 2
    assert "payload" not in _component(result, "audit_archive")["summary"]


def test_disabled_archive_is_not_an_incident_when_runtime_and_analysis_are_healthy() -> None:
    with patch("app.services.operations_health_service.runtime_readiness_report", return_value={"ready": True, "errors": [], "warnings": [], "readiness": {"environment": "production"}}), \
         patch("app.services.operations_health_service.analysis_operations_status", return_value={"store": "supabase", "execution_mode": "worker", "worker_required": True, "worker_available": True, "healthy_worker_count": 1, "queue": {}}), \
         patch("app.services.operations_health_service.audit_archive_operations_status", return_value={"mode": "disabled", "available": True, "delivery_ready": False, "workers": []}):
        result = operations_health_status()

    assert result["status"] == "healthy"
    assert _component(result, "audit_archive")["status"] == "disabled"
    assert result["incidents"] == []


def test_staff_operations_route_requires_operations_capability() -> None:
    async def run() -> None:
        user = CurrentUser(id="u1", auth_user_id="u1", email="operator@devbareun.test", role="operator")
        with patch("app.operations_routes.require_staff_permission") as permission, \
             patch("app.operations_routes.operations_health_status", return_value={"status": "healthy", "components": [], "incidents": []}):
            response = await get_operations_health(current_user=user)
        permission.assert_called_once_with(user, "operations")
        assert response["operations_health"]["status"] == "healthy"
    asyncio.run(run())


def test_super_admin_operations_health_uses_operations_permission_and_audits() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "operator@devbareun.test", "role": "operator"})) as require, \
             patch("app.saas_admin_routes.operations_health_status", return_value={"status": "degraded", "components": [], "incidents": [{"code": "analysis_worker_unavailable"}]}) as status, \
             patch("app.saas_admin_routes._audit") as audit:
            response = await admin_operations_health()
        assert response["operations_health"]["status"] == "degraded"
        require.assert_awaited_once()
        assert require.call_args.args[1] == "operations"
        status.assert_called_once()
        audit.assert_called_once()
        assert audit.call_args.args[1] == "view.operations_health"
    asyncio.run(run())


def test_operations_health_contract_files_are_linked() -> None:
    checker = importlib.import_module("check_operational_health")
    result = checker.check(ROOT)
    assert result.errors == []
