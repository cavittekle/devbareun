from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

pilot = importlib.import_module("pilot_acceptance")
checker = importlib.import_module("check_pilot_acceptance")


def parse_args(*items: str):
    return pilot.build_parser().parse_args(list(items))


def test_write_analysis_and_report_paths_require_explicit_confirmations() -> None:
    with pytest.raises(pilot.PilotAcceptanceError):
        pilot.validate_args(parse_args("--frontend-url", "https://frontend.test", "--backend-url", "https://backend.test", "--write"))
    with pytest.raises(pilot.PilotAcceptanceError):
        pilot.validate_args(parse_args(
            "--frontend-url", "https://frontend.test", "--backend-url", "https://backend.test",
            "--write", "--confirm-write", "PILOT_WRITE", "--run-analysis",
        ))
    with pytest.raises(pilot.PilotAcceptanceError):
        pilot.validate_args(parse_args(
            "--frontend-url", "https://frontend.test", "--backend-url", "https://backend.test",
            "--write", "--confirm-write", "PILOT_WRITE",
            "--run-analysis", "--confirm-analysis", "PILOT_ANALYSIS",
            "--generate-report",
        ))


def test_full_write_flow_argument_contract_is_valid_without_network() -> None:
    args = parse_args(
        "--frontend-url", "https://frontend.test", "--backend-url", "https://backend.test",
        "--write", "--confirm-write", "PILOT_WRITE",
        "--run-analysis", "--confirm-analysis", "PILOT_ANALYSIS",
        "--generate-report", "--confirm-report", "PILOT_REPORT",
        "--analysis-timeout", "300", "--cleanup",
    )
    pilot.validate_args(args)


def test_evidence_is_redacted_and_does_not_persist_secrets(tmp_path: Path) -> None:
    session = pilot.PilotSession(backend="https://backend.test", frontend="https://frontend.test")
    session.access_token = "secret-access-token"
    session.evidence.append(pilot.Evidence(label="authenticated session", ok=True, status=200, message="Access token accepted", ids={"project_id": "project-1"}))
    output = tmp_path / "evidence.json"
    pilot.write_evidence(output, session, "passed")
    text = output.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert "secret-access-token" not in text
    assert "authorization" not in text.lower()
    assert "project-1" in text
    assert payload["outcome"] == "passed"


def test_signed_upload_and_frontend_requests_explicitly_disable_session_auth() -> None:
    source = (ROOT / "tools" / "pilot_acceptance.py").read_text(encoding="utf-8")
    assert 'include_session_auth=False' in source
    assert 'session.request("GET", url, include_session_auth=False)' in source


def test_pilot_acceptance_static_contract_is_linked() -> None:
    result = checker.check(ROOT)
    assert result.errors == []
