from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.auth_dependencies import CurrentUser

PROJECT = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "project_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "user_id": "11111111-1111-1111-1111-111111111111",
    "owner_email": "owner@example.test",
    "company_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
}


def user(identifier: str, email: str) -> CurrentUser:
    return CurrentUser(id=identifier, auth_user_id=identifier, email=email, company_id=PROJECT["company_id"], role="customer")


def test_project_activity_scope_is_readable_by_viewer() -> None:
    sharing = importlib.import_module("app.services.project_sharing_service")
    activity = importlib.import_module("app.services.project_activity_service")
    viewer = user("22222222-2222-2222-2222-222222222222", "viewer@example.test")
    with patch.object(sharing, "is_configured", return_value=True),          patch.object(sharing, "_active_company_membership", return_value={"status": "active"}),          patch.object(sharing, "select_one", return_value={"project_role": "viewer", "status": "active"}),          patch.object(activity, "is_configured", return_value=True),          patch.object(activity, "select_rows", return_value=[{"event_id": "DB-ACT-ONE", "action": "analysis.completed", "metadata": {"token": "hidden", "risk_count": 2}, "created_at": "2026-06-21T00:00:00Z"}]):
        events = activity.list_project_activity(PROJECT, viewer)
    assert events[0]["action"] == "analysis.completed"
    assert events[0]["metadata"]["token"] == "[redacted]"


def test_project_activity_record_redacts_sensitive_storage_metadata() -> None:
    activity = importlib.import_module("app.services.project_activity_service")
    owner = user("11111111-1111-1111-1111-111111111111", "owner@example.test")
    captured = {}
    def _capture(table, payload):
        captured["table"] = table; captured["payload"] = payload; return payload
    with patch.object(activity, "is_configured", return_value=True), patch.object(activity, "insert_row", side_effect=_capture):
        activity.record_project_activity(PROJECT, owner, "upload.completed", "uploaded_file", "f1", {"storage_path": "private/path", "signed_url": "https://secret", "filename": "safe.xlsx"})
    assert captured["table"] == "project_activity_events"
    assert "storage_path" not in captured["payload"]["metadata"]
    assert "signed_url" not in captured["payload"]["metadata"]
    assert captured["payload"]["metadata"]["filename"] == "safe.xlsx"


def test_project_activity_routes_and_contract_are_registered() -> None:
    app = importlib.import_module("app.main").app
    keys = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    assert ("/api/project-activity/{project_id}", "GET") in keys
    checker = importlib.import_module("check_project_activity_timeline")
    result = checker.check(ROOT)
    assert result.errors == []
