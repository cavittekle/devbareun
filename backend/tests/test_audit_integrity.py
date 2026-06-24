from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.services.audit_service import build_audit_payload, metadata_sha256, record_audit_event, sanitize_metadata
from app.saas_admin_routes import admin_audit_integrity


def test_audit_metadata_redacts_secrets_and_hash_is_stable() -> None:
    raw = {
        "owner_email": "customer@example.com",
        "authorization": "Bearer secret-token",
        "nested": {"api_key": "do-not-store", "visible": "yes"},
    }
    safe = sanitize_metadata(raw)
    assert safe["authorization"] == "[redacted]"
    assert safe["nested"]["api_key"] == "[redacted]"
    assert safe["nested"]["visible"] == "yes"
    assert metadata_sha256(safe) == metadata_sha256(dict(safe))


def test_audit_payload_has_request_safe_fields_without_credentials() -> None:
    payload = build_audit_payload(
        {"email": "owner@devbareun.test", "role": "owner", "profile": {"auth_user_id": "auth-1"}},
        "adjust.credits",
        "credit_transactions",
        "credit-1",
        {"owner_email": "customer@example.com", "token": "must-not-leak"},
    )
    assert payload["p_event_category"] == "privileged_mutation"
    assert payload["p_severity"] == "high"
    assert payload["p_metadata"]["token"] == "[redacted]"
    assert payload["p_actor_user_id"] == "auth-1"
    assert len(payload["p_metadata_sha256"]) == 64


def test_production_audit_writer_uses_append_rpc() -> None:
    admin = {"email": "owner@devbareun.test", "role": "owner"}
    with patch("app.services.audit_service.is_configured", return_value=True), patch(
        "app.services.audit_service.call_rpc", return_value={"audit_id": "audit-1", "integrity_version": 1}
    ) as rpc:
        row = record_audit_event(admin, "update.staff", "users", "staff-1", {"staff_email": "staff@devbareun.test"})
    assert row and row["integrity_version"] == 1
    rpc.assert_called_once()
    assert rpc.call_args.args[0] == "append_audit_event"


def test_owner_audit_integrity_route_uses_safe_status() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "owner@devbareun.test", "role": "owner"})), patch(
            "app.saas_admin_routes.audit_integrity_status",
            return_value={"available": True, "verified": True, "checked_events": 4, "integrity_version": 1},
        ), patch("app.saas_admin_routes._audit") as audit:
            response = await admin_audit_integrity(limit=500)
        assert response["audit_integrity"]["verified"] is True
        audit.assert_called_once()
        assert audit.call_args.args[1] == "view.audit_integrity"

    asyncio.run(run())


def test_audit_integrity_contract_files_are_linked() -> None:
    import check_audit_integrity

    result = check_audit_integrity.check(ROOT)
    assert result.errors == []
