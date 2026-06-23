from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.access_control import has_permission
from app.auth_dependencies import CurrentUser
from app.services.data_lifecycle_service import (
    ERASURE_CONFIRMATION,
    admin_safe_row,
    customer_safe_row,
    policy_from_env,
    request_payload,
    soft_delete_schedule,
    validate_erasure_confirmation,
    validate_request_scope,
)


def test_lifecycle_policy_enforces_safe_ranges() -> None:
    policy = policy_from_env({
        "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS": "30",
        "DEVBAREUN_ERASURE_GRACE_DAYS": "14",
        "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS": "7",
        "DEVBAREUN_AUTO_PURGE_ENABLED": "false",
    })
    assert policy.soft_delete_retention_days == 30
    assert policy.auto_purge_enabled is False
    with pytest.raises(ValueError):
        policy_from_env({"DEVBAREUN_SOFT_DELETE_RETENTION_DAYS": "3"})


def test_erasure_requires_explicit_confirmation_and_project_scope_is_strict() -> None:
    validate_erasure_confirmation(ERASURE_CONFIRMATION)
    with pytest.raises(ValueError):
        validate_erasure_confirmation("delete")
    assert validate_request_scope("project", "project-1") == ("project", "project-1")
    with pytest.raises(ValueError):
        validate_request_scope("project", None)
    with pytest.raises(ValueError):
        validate_request_scope("account", "project-1")


def test_soft_delete_schedule_is_deterministic_for_fixed_policy() -> None:
    policy = policy_from_env({
        "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS": "30",
        "DEVBAREUN_ERASURE_GRACE_DAYS": "14",
        "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS": "7",
        "DEVBAREUN_AUTO_PURGE_ENABLED": "false",
    })
    schedule = soft_delete_schedule(now=datetime(2026, 6, 21, tzinfo=timezone.utc), policy=policy)
    assert schedule["retention_status"] == "soft_deleted"
    assert schedule["deleted_at"] == "2026-06-21T00:00:00Z"
    assert schedule["purge_after_at"] == "2026-07-21T00:00:00Z"


def test_request_payload_carries_grace_without_storing_confirmation() -> None:
    policy = policy_from_env({
        "DEVBAREUN_SOFT_DELETE_RETENTION_DAYS": "30",
        "DEVBAREUN_ERASURE_GRACE_DAYS": "14",
        "DEVBAREUN_PRIVACY_EXPORT_REQUEST_TTL_DAYS": "7",
        "DEVBAREUN_AUTO_PURGE_ENABLED": "false",
    })
    row = request_payload(
        lifecycle_request_id="DB-PRV-TEST",
        requester_email="customer@example.test",
        requester_user_id="00000000-0000-0000-0000-000000000001",
        request_type="erasure",
        scope="account",
        project_id=None,
        reason="Closing account",
        request_id="request-1",
        now=datetime(2026, 6, 21, tzinfo=timezone.utc),
        policy=policy,
    )
    assert row["grace_expires_at"] == "2026-07-05T00:00:00Z"
    assert row["scheduled_purge_at"] is None
    assert "confirmation" not in row


def test_customer_and_admin_shapes_redact_internal_or_storage_data() -> None:
    raw = {
        "lifecycle_request_id": "DB-PRV-TEST",
        "requester_user_id": "secret-user-id",
        "requester_email": "customer@example.test",
        "request_type": "export",
        "scope": "account",
        "status": "requested",
        "reviewed_by": "owner@example.test",
        "review_note": "Internal review note",
        "storage_path": "private/path",
        "export_payload": {"raw": "data"},
        "metadata": {"private": True},
    }
    customer = customer_safe_row(raw)
    admin = admin_safe_row(raw)
    assert "requester_user_id" not in customer
    assert "review_note" not in customer
    assert "storage_path" not in customer
    assert "export_payload" not in admin
    assert "storage_path" not in admin
    assert "metadata" not in admin


def test_only_owner_has_internal_privacy_capability() -> None:
    assert has_permission("owner", "privacy") is True
    for role in ("customer", "support", "analyst", "finance", "operator"):
        assert has_permission(role, "privacy") is False


def test_duplicate_active_request_returns_existing_row_without_second_insert() -> None:
    routes = importlib.import_module("app.data_lifecycle_routes")
    user = CurrentUser(
        id="user-1",
        auth_user_id="00000000-0000-0000-0000-000000000001",
        email="customer@example.test",
    )
    existing = {
        "lifecycle_request_id": "DB-PRV-OLD",
        "requester_email": user.email,
        "request_type": "export",
        "scope": "account",
        "status": "requested",
    }
    with patch.object(routes, "_owned_rows", return_value=[existing]), patch.object(routes, "_insert_request") as insert_request:
        response = routes._create_request(user, request_type="export", scope="account", project_id=None, reason=None)
    assert response["deduplicated"] is True
    assert response["request"]["lifecycle_request_id"] == "DB-PRV-OLD"
    insert_request.assert_not_called()


def test_static_contract_and_api_contract_include_data_lifecycle() -> None:
    checker = importlib.import_module("check_data_lifecycle")
    result = checker.check(ROOT)
    assert result.errors == []
    api = importlib.import_module("export_api_contract")
    contract = api.check_contract(ROOT)
    assert contract.errors == []


def test_workspace_settings_exposes_guarded_privacy_request_workflow() -> None:
    client = (ROOT / "frontend/member-dashboard-app/src/api/client.js").read_text(encoding="utf-8")
    settings = (ROOT / "frontend/member-dashboard-app/src/pages/Settings.jsx").read_text(encoding="utf-8")
    assert "requestDataExport" in client
    assert "requestDataErasure" in client
    assert "cancelPrivacyRequest" in client
    assert "ERASE MY DATA" in settings
    assert "No data was deleted automatically" in settings
