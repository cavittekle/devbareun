from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.saas_admin_routes import admin_audit_archive, admin_retry_audit_archive
from app.saas_common import AuditArchiveRetryRequest
from app.services.audit_archive_service import audit_archive_operations_status, drain_audit_archive_once


def _claimed_row() -> dict:
    return {
        "archive_id": "archive-1",
        "audit_id": "audit-1",
        "lease_token": "lease-1",
        "attempts": 1,
        "integrity_version": 1,
        "event_hash": "event-hash",
        "previous_event_hash": "GENESIS_V1424",
        "payload_sha256": "payload-hash",
        "created_at": "2026-06-20T00:00:00Z",
        "payload": {"audit_id": "audit-1", "metadata": {"visible": True}},
    }


def test_archive_worker_claims_delivers_and_acknowledges() -> None:
    row = _claimed_row()
    with patch("app.services.audit_archive_service.is_configured", return_value=True), \
         patch("app.services.audit_archive_service.audit_archive_mode", return_value="webhook"), \
         patch("app.services.audit_archive_service.audit_archive_delivery_ready", return_value=True), \
         patch("app.services.audit_archive_service.call_rpc", side_effect=[[row], {"archive_id": "archive-1", "status": "delivered"}]) as rpc, \
         patch("app.services.audit_archive_service._post_webhook", return_value="receiver-1") as post, \
         patch("app.services.audit_archive_service.record_audit_archive_worker_heartbeat") as heartbeat:
        result = drain_audit_archive_once(worker_id="archive-worker-1", batch_size=1)

    assert result["claimed"] == 1
    assert result["delivered"] == 1
    assert result["dead_lettered"] == 0
    post.assert_called_once()
    assert [call.args[0] for call in rpc.call_args_list] == ["claim_audit_archive_outbox", "record_audit_archive_delivery"]
    heartbeat.assert_called_once()


def test_archive_worker_records_dead_letter_without_retrying_payload() -> None:
    row = _claimed_row()
    with patch("app.services.audit_archive_service.is_configured", return_value=True), \
         patch("app.services.audit_archive_service.audit_archive_mode", return_value="webhook"), \
         patch("app.services.audit_archive_service.audit_archive_delivery_ready", return_value=True), \
         patch("app.services.audit_archive_service.call_rpc", side_effect=[[row], {"archive_id": "archive-1", "status": "dead_lettered"}]) as rpc, \
         patch("app.services.audit_archive_service._post_webhook", side_effect=RuntimeError("archive_webhook_http_503")), \
         patch("app.services.audit_archive_service.record_audit_archive_worker_heartbeat"):
        result = drain_audit_archive_once(worker_id="archive-worker-1", batch_size=1)

    assert result["claimed"] == 1
    assert result["delivered"] == 0
    assert result["dead_lettered"] == 1
    assert [call.args[0] for call in rpc.call_args_list] == ["claim_audit_archive_outbox", "record_audit_archive_failure"]


def test_archive_status_never_returns_webhook_configuration_or_payload() -> None:
    with patch("app.services.audit_archive_service.is_configured", return_value=True), \
         patch("app.services.audit_archive_service.audit_archive_mode", return_value="webhook"), \
         patch("app.services.audit_archive_service.audit_archive_delivery_ready", return_value=True), \
         patch("app.services.audit_archive_service.call_rpc", return_value={"available": True, "pending": 2, "recent_dead_lettered": []}), \
         patch("app.services.audit_archive_service.select_rows", return_value=[{"worker_id": "worker-1", "status": "online"}]):
        status = audit_archive_operations_status()

    assert status["pending"] == 2
    assert status["workers"][0]["worker_id"] == "worker-1"
    assert "webhook_url" not in status
    assert "webhook_secret" not in status
    assert "payload" not in status


def test_owner_only_archive_retry_route() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "owner@devbareun.test", "role": "owner"})), \
             patch("app.saas_admin_routes.retry_audit_archive_item", return_value={"archive_id": "archive-1", "status": "pending"}) as retry, \
             patch("app.saas_admin_routes._audit") as audit:
            response = await admin_retry_audit_archive("archive-1", AuditArchiveRetryRequest(reset_attempts=True))
        assert response["audit_archive_item"]["status"] == "pending"
        assert retry.call_args.kwargs["reset_attempts"] is True
        audit.assert_called_once()

    asyncio.run(run())


def test_non_owner_cannot_retry_audit_archive() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "support@devbareun.test", "role": "support"})), \
             patch("app.saas_admin_routes.retry_audit_archive_item") as retry:
            with pytest.raises(HTTPException) as raised:
                await admin_retry_audit_archive("archive-1", AuditArchiveRetryRequest(reset_attempts=True))
        assert raised.value.status_code == 403
        retry.assert_not_called()

    asyncio.run(run())


def test_audit_archive_read_route_uses_safe_operations_status() -> None:
    async def run() -> None:
        with patch("app.saas_admin_routes.require_super_admin_user", AsyncMock(return_value={"email": "owner@devbareun.test", "role": "owner"})), \
             patch("app.saas_admin_routes.audit_archive_operations_status", return_value={"available": True, "pending": 1, "workers": []}), \
             patch("app.saas_admin_routes._audit") as audit:
            response = await admin_audit_archive(limit=50)
        assert response["audit_archive"]["pending"] == 1
        audit.assert_called_once()
        assert audit.call_args.args[1] == "view.audit_archive"

    asyncio.run(run())


def test_audit_archive_contract_files_are_linked() -> None:
    checker = importlib.import_module("check_audit_archive_outbox")
    result = checker.check(ROOT)
    assert result.errors == []
