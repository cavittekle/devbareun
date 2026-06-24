from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from app.upload_security import UploadSecurityScreeningError, screen_materialized_upload


def _xlsx(path: Path, *, macro: bool = False, payload_size: int = 0) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("xl/workbook.xml", "<workbook />")
        if payload_size:
            archive.writestr("xl/worksheets/sheet1.xml", "A" * payload_size)
        if macro:
            archive.writestr("xl/vbaProject.bin", b"macro-bytes")


def _row(filename: str) -> dict:
    return {"original_filename": filename, "upload_status": "uploaded", "status": "uploaded", "parser_status": "pending"}


def test_clean_xlsx_is_released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS", "false")
    path = tmp_path / "safe.xlsx"
    _xlsx(path)
    row = _row(path.name)
    outcome = screen_materialized_upload(row, path)
    assert outcome["status"] == "clean"
    assert row["security_scan_status"] == "clean"
    assert row["quarantine_status"] == "released"
    assert row["security_scan_findings"] == []


def test_suspicious_office_compression_ratio_is_quarantined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO", "10")
    path = tmp_path / "compressed.xlsx"
    _xlsx(path, payload_size=100_000)
    row = _row(path.name)
    with pytest.raises(UploadSecurityScreeningError, match="compression ratio") as raised:
        screen_materialized_upload(row, path)
    assert raised.value.code == "office_archive_compression_ratio"
    assert row["security_scan_status"] == "blocked"
    assert row["quarantine_status"] == "quarantined"
    assert row["upload_status"] == "quarantined"


def test_macro_workbook_is_recorded_or_blocked_by_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "schedule.xlsm"
    _xlsx(path, macro=True)
    monkeypatch.setenv("DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS", "false")
    row = _row(path.name)
    screen_materialized_upload(row, path)
    assert row["security_scan_status"] == "clean"
    assert any(item["code"] == "macro_enabled_workbook" for item in row["security_scan_findings"])

    monkeypatch.setenv("DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS", "true")
    blocked = _row(path.name)
    with pytest.raises(UploadSecurityScreeningError, match="Macro-enabled"):
        screen_materialized_upload(blocked, path)
    assert blocked["security_scan_status"] == "blocked"
    assert blocked["quarantine_reason"] == "macro_enabled_workbook"


def test_active_pdf_can_be_blocked_by_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "active.pdf"
    path.write_bytes(b"%PDF-1.7\n1 0 obj\n/JavaScript (app.alert('x'))\nendobj\n")
    monkeypatch.setenv("DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT", "true")
    row = _row(path.name)
    with pytest.raises(UploadSecurityScreeningError, match="active content"):
        screen_materialized_upload(row, path)
    assert row["security_scan_status"] == "blocked"
    assert row["quarantine_status"] == "quarantined"


def test_screening_contract_files_exist():
    root = Path(__file__).resolve().parents[2]
    migration = root / "database/2026_06_19_v1421_upload_security_screening.sql"
    docs = root / "docs/UPLOAD_SECURITY_SCREENING_V1421.md"
    assert migration.exists()
    assert docs.exists()
    assert migration.name in (root / "database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
    assert "not an antivirus" in docs.read_text(encoding="utf-8").lower()
