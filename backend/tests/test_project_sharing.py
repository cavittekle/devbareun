from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.auth_dependencies import CurrentUser, _project_belongs_to_user

PROJECT = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "user_id": "11111111-1111-1111-1111-111111111111",
    "owner_email": "owner@example.test",
    "company_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
}


def user(identifier: str, email: str, role: str = "customer") -> CurrentUser:
    return CurrentUser(
        id=identifier,
        auth_user_id=identifier,
        email=email,
        company_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        role=role,
    )


def test_owner_has_implicit_full_project_access() -> None:
    service = importlib.import_module("app.services.project_sharing_service")
    owner = user("11111111-1111-1111-1111-111111111111", "owner@example.test")
    assert service.project_access_role(PROJECT, owner) == "owner"
    assert service.can_access_project_resource(PROJECT, owner, "project_delete")


def test_company_membership_alone_does_not_grant_project_access() -> None:
    service = importlib.import_module("app.services.project_sharing_service")
    teammate = user("22222222-2222-2222-2222-222222222222", "member@example.test")
    membership = {"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "status": "active"}
    with patch.object(service, "is_configured", return_value=True), \
         patch.object(service, "_active_company_membership", return_value=membership), \
         patch.object(service, "select_one", return_value=None):
        assert service.project_access_role(PROJECT, teammate) is None
        assert not _project_belongs_to_user(PROJECT, teammate, section="projects")


def test_viewer_can_read_but_cannot_operate_project() -> None:
    service = importlib.import_module("app.services.project_sharing_service")
    teammate = user("22222222-2222-2222-2222-222222222222", "member@example.test")
    membership = {"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "status": "active"}
    grant = {"project_role": "viewer", "status": "active"}
    with patch.object(service, "is_configured", return_value=True), \
         patch.object(service, "_active_company_membership", return_value=membership), \
         patch.object(service, "select_one", return_value=grant):
        assert service.can_access_project_resource(PROJECT, teammate, "dashboard")
        assert service.can_access_project_resource(PROJECT, teammate, "reports")
        assert not service.can_access_project_resource(PROJECT, teammate, "uploads")
        assert not service.can_access_project_resource(PROJECT, teammate, "analysis_run")
        assert not service.can_access_project_resource(PROJECT, teammate, "project_access_manage")


def test_editor_and_manager_have_intentionally_different_scope() -> None:
    service = importlib.import_module("app.services.project_sharing_service")
    teammate = user("22222222-2222-2222-2222-222222222222", "member@example.test")
    membership = {"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "status": "active"}
    for role, expected_manage in (("editor", False), ("manager", True)):
        with patch.object(service, "is_configured", return_value=True), \
             patch.object(service, "_active_company_membership", return_value=membership), \
             patch.object(service, "select_one", return_value={"project_role": role, "status": "active"}):
            assert service.can_access_project_resource(PROJECT, teammate, "uploads")
            assert service.can_access_project_resource(PROJECT, teammate, "analysis_run")
            assert service.can_access_project_resource(PROJECT, teammate, "project_access_manage") is expected_manage
            assert not service.can_access_project_resource(PROJECT, teammate, "project_delete")


def test_grant_rejects_project_owner() -> None:
    service = importlib.import_module("app.services.project_sharing_service")
    owner = user("11111111-1111-1111-1111-111111111111", "owner@example.test")
    membership = {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "company_id": PROJECT["company_id"],
        "user_id": owner.id,
        "member_email": owner.email,
        "status": "active",
    }
    with patch.object(service, "_require_project_manager", return_value=(PROJECT["id"], PROJECT["company_id"])), \
         patch.object(service, "_membership_for_company", return_value=membership):
        with pytest.raises(ValueError):
            service.grant_project_access(PROJECT, owner, membership_id=membership["id"], project_role="viewer")


def test_project_access_routes_are_in_openapi() -> None:
    app = importlib.import_module("app.main").app
    keys = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    for path, method in (
        ("/api/project-access/projects", "GET"),
        ("/api/project-access/{project_id}/members", "GET"),
        ("/api/project-access/{project_id}/members", "POST"),
        ("/api/project-access/{project_id}/members/{grant_id}", "PATCH"),
        ("/api/project-access/{project_id}/members/{grant_id}", "DELETE"),
    ):
        assert (path, method) in keys


def test_project_sharing_contract_checker_passes() -> None:
    checker = importlib.import_module("check_project_sharing")
    result = checker.check(ROOT)
    assert result.errors == []
