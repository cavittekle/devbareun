from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.file_validation import normalize_sha256_checksum
from app.services.parser_service import _verify_materialized_checksum


def test_normalize_sha256_checksum_accepts_valid_digest():
    digest = "A" * 64
    assert normalize_sha256_checksum(digest) == "a" * 64


def test_normalize_sha256_checksum_rejects_invalid_digest():
    with pytest.raises(ValueError):
        normalize_sha256_checksum("not-a-digest")


def test_materialized_file_checksum_is_verified(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_bytes(b"quantity,cost\n1,100\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    row = {"original_filename": source.name, "checksum": digest}
    _verify_materialized_checksum(row, source)
    assert row["checksum_status"] == "verified"
    assert row["verified_checksum"] == digest


def test_materialized_file_checksum_mismatch_is_visible(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_bytes(b"quantity,cost\n1,100\n")
    row = {"original_filename": source.name, "checksum": "0" * 64}
    with pytest.raises(ValueError, match="checksum"):
        _verify_materialized_checksum(row, source)
    assert row["checksum_status"] == "mismatch"
    assert row["checksum_error"] == "checksum_mismatch"


def test_upload_checksum_contract_files_exist():
    root = Path(__file__).resolve().parents[2]
    assert (root / "database/2026_06_19_v1420_upload_checksum_integrity.sql").exists()
    assert (root / "docs/UPLOAD_CHECKSUM_INTEGRITY_V1420.md").exists()
    assert "2026_06_19_v1420_upload_checksum_integrity.sql" in (root / "database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
