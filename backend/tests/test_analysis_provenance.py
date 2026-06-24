from __future__ import annotations

from pathlib import Path

from app.services.analysis_provenance import build_analysis_input_manifest
from app.services.dashboard_service import build_executive_dashboard
from app.services.report_service import legacy_report_payload


def _source(file_id: str, *, filename: str, checksum: str, verified: str | None = None) -> dict:
    return {
        "id": file_id,
        "file_id": file_id,
        "original_filename": filename,
        "file_ext": filename.rsplit(".", 1)[-1],
        "size_bytes": 128,
        "checksum": checksum,
        "verified_checksum": verified,
        "checksum_status": "verified" if verified else "pending_verification",
        "checksum_verified_at": "2026-06-19T10:00:00+00:00" if verified else None,
        "security_scan_status": "clean",
        "security_scan_engine": "devbareun_deterministic_admission_v1",
        "security_scan_completed_at": "2026-06-19T10:00:01+00:00",
        "quarantine_status": "released",
        "parser_status": "parsed",
        "storage_path": "private/do-not-expose/source.xlsx",
        "signed_download_url": "https://example.invalid/secret",
        "user_id": "private-user-id",
    }


def test_input_manifest_is_deterministic_and_excludes_storage_secrets():
    first = _source("b", filename="second.xlsx", checksum="b" * 64, verified="c" * 64)
    second = _source("a", filename="first.pdf", checksum="a" * 64)

    left = build_analysis_input_manifest([first, second])
    right = build_analysis_input_manifest([second, first])

    assert left["file_count"] == 2
    assert left["source_fingerprint"] == right["source_fingerprint"]
    assert [row["file_id"] for row in left["files"]] == ["a", "b"]
    assert left["files"][1]["content_sha256"] == "c" * 64
    assert left["files"][1]["content_hash_source"] == "verified"
    rendered = str(left)
    assert "private/do-not-expose" not in rendered
    assert "signed_download_url" not in rendered
    assert "private-user-id" not in rendered


def test_executive_dashboard_and_report_keep_safe_provenance():
    provenance = build_analysis_input_manifest([_source("a", filename="cost.xlsx", checksum="a" * 64)])
    result = {
        "created_at": "2026-06-19T10:00:00+00:00",
        "confidence_score": 85,
        "input_manifest": provenance,
        "dashboard_data": {"metrics": {}, "document_control": {}, "project": {"name": "Test", "currency": "AZN"}},
        "normalized_data": {"warnings": [], "evidence": {"sheet_profiles": []}},
        "risk_data": [],
    }
    project = {"id": "project-1", "project_id": "project-1", "project_name": "Test", "currency": "AZN"}

    dashboard = build_executive_dashboard(project=project, analysis_result=result)
    report = legacy_report_payload(project, result)

    assert dashboard["analysis_provenance"]["source_fingerprint"] == provenance["source_fingerprint"]
    assert report["dashboard"]["analysis_provenance"]["file_count"] == 1
    assert "storage_path" not in str(report)


def test_provenance_contract_files_are_registered():
    root = Path(__file__).resolve().parents[2]
    migration = root / "database/2026_06_19_v1422_analysis_input_provenance.sql"
    docs = root / "docs/ANALYSIS_INPUT_PROVENANCE_V1422.md"
    assert migration.exists()
    assert docs.exists()
    assert migration.name in (root / "database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8")
    assert "tools/check_analysis_provenance.py" in (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
