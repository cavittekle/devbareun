from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.access_control import can_access_project_scope, can_operate_analysis_jobs, has_permission, normalize_role
from app.analysis_routes import _require_staff_operations
from app.auth_dependencies import CurrentUser, _project_belongs_to_user
from app.saas_admin_routes import admin_update_customer_status
from app.services.analysis_job_service import _row_belongs_to_user as analysis_row_visible
from app.services.report_service import _row_belongs_to_user as report_row_visible
from app.upload_routes import _file_belongs_to_user


def user(role: str, email: str = "staff@devbareun.test") -> CurrentUser:
    return CurrentUser(id="user-id", auth_user_id="auth-id", email=email, role=role, is_admin=(role == "owner"))


def test_canonical_roles_and_permissions_are_least_privilege() -> None:
    assert normalize_role("admin") == "owner"
    assert normalize_role("user") == "customer"
    assert has_permission("owner", "staff")
    assert has_permission("operator", "operations")
    assert not has_permission("analyst", "operations")
    assert not has_permission("support", "projects")
    assert has_permission("analyst", "uploads")
    assert not has_permission("operator", "uploads")
    assert has_permission("finance", "credits")
    assert not has_permission("finance", "reports")
    assert can_access_project_scope("analyst", "projects")
    assert not can_access_project_scope("finance", "projects")
    assert can_operate_analysis_jobs("owner")
    assert can_operate_analysis_jobs("operator")
    assert not can_operate_analysis_jobs("support")


def test_project_file_analysis_and_report_data_use_resource_capabilities() -> None:
    project = {"owner_email": "customer@example.com", "user_id": "customer-id"}
    file_row = {"owner_email": "customer@example.com", "user_id": "customer-id"}
    report_row = {"owner_email": "customer@example.com", "user_id": "customer-id"}
    analysis_row = {"owner_email": "customer@example.com", "user_id": "customer-id"}

    assert not _project_belongs_to_user(project, user("support"), section="projects")
    assert not _project_belongs_to_user(project, user("finance"), section="projects")
    assert _project_belongs_to_user(project, user("analyst"), section="projects")
    assert _project_belongs_to_user(project, user("operator"), section="projects")

    assert not _file_belongs_to_user(file_row, user("support"))
    assert not _file_belongs_to_user(file_row, user("finance"))
    assert _file_belongs_to_user(file_row, user("analyst"))
    assert not _file_belongs_to_user(file_row, user("operator"))

    assert not analysis_row_visible(analysis_row, user("support"))
    assert not analysis_row_visible(analysis_row, user("finance"))
    assert analysis_row_visible(analysis_row, user("analyst"))
    assert analysis_row_visible(analysis_row, user("operator"))

    assert not report_row_visible(report_row, user("support"))
    assert not report_row_visible(report_row, user("finance"))
    assert report_row_visible(report_row, user("analyst"))
    assert report_row_visible(report_row, user("operator"))


def test_worker_operations_are_owner_or_operator_only() -> None:
    _require_staff_operations(user("owner"))
    _require_staff_operations(user("operator"))
    for role in ("support", "analyst", "finance", "customer"):
        with pytest.raises(HTTPException) as raised:
            _require_staff_operations(user(role))
        assert raised.value.status_code == 403


def test_customer_status_route_refuses_to_mutate_staff_profile() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "owner@devbareun.test", "role": "owner"})), \
             patch("app.saas_admin_routes._production_rows", return_value=[{"email": "finance@devbareun.test", "role": "finance"}]), \
             patch("app.saas_admin_routes._production_update") as update:
            from app.saas_common import CustomerStatusRequest
            with pytest.raises(HTTPException) as raised:
                await admin_update_customer_status("finance@devbareun.test", CustomerStatusRequest(status="suspended"))
            assert raised.value.status_code == 403
            update.assert_not_called()

    asyncio.run(run())


def test_panel_access_contract_files_are_linked() -> None:
    migration = ROOT / "database/2026_06_20_v1423_panel_access_boundaries.sql"
    doc = ROOT / "docs/PANEL_ACCESS_BOUNDARIES_V1423.md"
    deploy_order = (ROOT / "database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
    assert migration.exists()
    assert doc.exists()
    assert migration.name in deploy_order
    assert "operations" in doc.read_text(encoding="utf-8")
