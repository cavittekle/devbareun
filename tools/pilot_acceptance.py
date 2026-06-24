#!/usr/bin/env python3
"""Run a guarded DevBareun production-pilot acceptance check.

This tool is intentionally dependency-free and opt-in for every state-changing
operation. It supports either a short-lived Supabase access token or a pilot
login whose password is read from an environment variable. It never prints
Authorization headers, cookies, passwords, signed URLs, or raw API payloads.

Examples:
  # Read-only authenticated verification
  DEVBAREUN_E2E_ACCESS_TOKEN='...' python tools/pilot_acceptance.py \
    --frontend-url https://devbareun.com \
    --backend-url https://api.example.com

  # Controlled write/pilot flow using a dedicated non-production customer
  DEVBAREUN_E2E_PASSWORD='...' python tools/pilot_acceptance.py \
    --frontend-url https://staging.devbareun.com \
    --backend-url https://api-staging.example.com \
    --login-email pilot@example.com \
    --write --confirm-write PILOT_WRITE --cleanup
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

READ_ONLY_PATHS = (
    "index.html",
    "workspace/",
)

CSRF_COOKIE = "devbareun_csrf"
WRITE_CONFIRMATION = "PILOT_WRITE"
ANALYSIS_CONFIRMATION = "PILOT_ANALYSIS"
REPORT_CONFIRMATION = "PILOT_REPORT"


class PilotAcceptanceError(RuntimeError):
    """A controlled acceptance check failed."""


@dataclass
class Evidence:
    label: str
    ok: bool
    status: int | None
    message: str
    ids: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "ids": dict(self.ids),
        }


@dataclass
class PilotSession:
    backend: str
    frontend: str
    access_token: str = ""
    cookies: CookieJar = field(default_factory=CookieJar)
    evidence: List[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.backend = normalize_base(self.backend)
        self.frontend = normalize_base(self.frontend)
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def csrf_token(self) -> str:
        for cookie in self.cookies:
            if cookie.name == CSRF_COOKIE:
                return cookie.value
        return ""

    def _headers(self, method: str, extra: Optional[Mapping[str, str]] = None, *, include_session_auth: bool = True) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "DevBareunPilotAcceptance/1.4.27",
        }
        if include_session_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if include_session_auth and method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            csrf = self.csrf_token()
            if csrf:
                headers["X-CSRF-Token"] = csrf
        if extra:
            headers.update({key: value for key, value in extra.items() if value is not None})
        return headers

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        raw: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: int = 30,
        include_session_auth: bool = True,
    ) -> tuple[int, Dict[str, Any], str]:
        url = path_or_url if path_or_url.startswith("http://") or path_or_url.startswith("https://") else urljoin(self.backend, path_or_url.lstrip("/"))
        data: Optional[bytes] = raw
        merged_headers = self._headers(method, headers, include_session_auth=include_session_auth)
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            merged_headers.setdefault("Content-Type", "application/json")
        request = Request(url, data=data, headers=merged_headers, method=method.upper())
        try:
            with self.opener.open(request, timeout=timeout) as response:
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
                return response.status, parse_json(body), body
        except HTTPError as exc:
            body = exc.read(1024 * 512).decode("utf-8", errors="replace")
            return exc.code, parse_json(body), body
        except URLError as exc:
            raise PilotAcceptanceError(f"network error for {safe_url(path_or_url)}: {exc.reason}") from exc
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise PilotAcceptanceError(f"request error for {safe_url(path_or_url)}: {exc}") from exc

    def record(self, label: str, status: int | None, *, expected: Iterable[int] | range = range(200, 300), ids: Optional[Mapping[str, str]] = None, message: str = "") -> None:
        expected_set = set(expected)
        ok = status in expected_set if status is not None else False
        evidence = Evidence(label=label, ok=ok, status=status, message=message or f"HTTP {status}", ids=dict(ids or {}))
        self.evidence.append(evidence)
        prefix = "PASS" if ok else "FAIL"
        print(f"[{prefix}] {label}: {evidence.message}")
        if not ok:
            raise PilotAcceptanceError(f"{label} failed: {evidence.message}")


def normalize_base(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        raise PilotAcceptanceError("base URLs must begin with http:// or https://")
    return cleaned.rstrip("/") + "/"


def safe_url(value: str) -> str:
    """Avoid echoing signed-query tokens when an exception references a URL."""
    return value.split("?", 1)[0]


def parse_json(body: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(body)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise PilotAcceptanceError(f"missing required environment variable: {name}")
    return value


def require_confirmation(enabled: bool, provided: str, expected: str, label: str) -> None:
    if enabled and provided != expected:
        raise PilotAcceptanceError(f"{label} requires --confirm-{label} {expected}")


def pilot_csv() -> bytes:
    return (
        "work_item,planned_amount,actual_amount,planned_progress,actual_progress\n"
        "Concrete preparation,10000,4000,100,40\n"
        "Masonry works,25000,0,60,0\n"
    ).encode("utf-8")


def short_id(value: Any) -> str:
    return str(value or "").strip()[:96]


def extract_id(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def init_csrf(session: PilotSession) -> None:
    status, payload, _ = session.request("GET", "/api/auth/csrf")
    token = session.csrf_token() or str(payload.get("csrf_token") or "")
    session.record("csrf initializer", status, message="CSRF cookie initialized" if token else "CSRF endpoint returned no token")
    if not token:
        raise PilotAcceptanceError("CSRF initializer did not provide a token or cookie")


def authenticate(session: PilotSession, args: argparse.Namespace) -> None:
    access_token = os.getenv(args.access_token_env, "").strip()
    if access_token:
        session.access_token = access_token
        status, payload, _ = session.request("GET", "/api/auth/me")
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        session.record("authenticated session", status, ids={"user": short_id(user.get("id") or user.get("user_id"))}, message="Access token accepted")
        return

    if not args.login_email:
        raise PilotAcceptanceError(
            f"set {args.access_token_env} or pass --login-email with a password available in {args.password_env}"
        )
    password = require_env(args.password_env)
    status, payload, _ = session.request(
        "POST",
        "/api/auth/supabase/login",
        payload={"email": args.login_email, "password": password},
    )
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    session.record("Supabase pilot login", status, ids={"user": short_id(user.get("id") or user.get("user_id"))}, message="Login completed")
    # The backend sets an HttpOnly cookie. Do not use or print the returned auth payload.
    status, payload, _ = session.request("GET", "/api/auth/me")
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    session.record("authenticated session", status, ids={"user": short_id(user.get("id") or user.get("user_id"))}, message="Cookie session accepted")


def public_checks(session: PilotSession, strict: bool) -> None:
    for relative in READ_ONLY_PATHS:
        url = urljoin(session.frontend, relative)
        status, _, _ = session.request("GET", url, include_session_auth=False)
        session.record(f"frontend {relative}", status)
    for label, endpoint in (
        ("backend health", "/api/health"),
        ("backend readiness", "/api/readiness"),
        ("backend version", "/api/version"),
    ):
        status, payload, _ = session.request("GET", endpoint)
        session.record(label, status)
        if label == "backend readiness":
            readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
            ready = payload.get("ready") if "ready" in payload else readiness.get("ready")
            if strict and ready is not True:
                raise PilotAcceptanceError("backend readiness is not production-ready")


def create_project(session: PilotSession, project_name: str) -> str:
    status, payload, _ = session.request(
        "POST",
        "/api/projects/create",
        payload={
            "project_name": project_name,
            "location": "Pilot acceptance environment",
            "contractor": "DevBareun pilot",
            "client": "DevBareun pilot",
            "currency": "AZN",
            "project_status": "draft",
            "analysis_type": "all",
        },
    )
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    project_id = extract_id(project, "project_id", "id")
    session.record("create pilot project", status, ids={"project_id": short_id(project_id)}, message="Pilot project created")
    if not project_id:
        raise PilotAcceptanceError("project creation response did not contain project_id")
    return project_id


def upload_fixture(session: PilotSession, project_id: str) -> str:
    content = pilot_csv()
    checksum = hashlib.sha256(content).hexdigest()
    status, payload, _ = session.request(
        "POST",
        "/api/uploads/create-url",
        payload={
            "project_id": project_id,
            "filename": "devbareun-pilot-smoke.csv",
            "mime_type": "text/csv",
            "size_bytes": len(content),
            "checksum": checksum,
        },
    )
    file_id = extract_id(payload, "upload_id", "file_id")
    storage_path = str(payload.get("storage_path") or "")
    signed_url = str(payload.get("signed_upload_url") or "")
    session.record("create signed upload", status, ids={"file_id": short_id(file_id)}, message="Upload metadata accepted")
    if not file_id or not storage_path:
        raise PilotAcceptanceError("upload-url response did not contain file_id/storage_path")
    if not signed_url:
        raise PilotAcceptanceError("production pilot requires a signed upload URL; local metadata mode is not accepted")

    status, _, _ = session.request(
        "PUT",
        signed_url,
        raw=content,
        headers={"Content-Type": "text/csv"},
        timeout=60,
        include_session_auth=False,
    )
    # Signed storage URLs can return 200/201/204 depending on provider version.
    session.record("upload pilot fixture", status, expected={200, 201, 204}, ids={"file_id": short_id(file_id)}, message="Fixture stored")

    status, _, _ = session.request(
        "POST",
        "/api/uploads/mark-uploaded",
        payload={
            "upload_id": file_id,
            "project_id": project_id,
            "storage_path": storage_path,
            "uploaded": True,
            "checksum": checksum,
        },
    )
    session.record("mark upload complete", status, ids={"file_id": short_id(file_id)}, message="Upload admitted for screening")

    status, payload, _ = session.request("GET", f"/api/uploads/project/{project_id}")
    rows = payload.get("uploaded_files") if isinstance(payload.get("uploaded_files"), list) else []
    found = any(str(row.get("file_id") or row.get("id") or "") == file_id for row in rows if isinstance(row, dict))
    session.record("verify uploaded file", status, ids={"file_id": short_id(file_id)}, message="Upload record listed" if found else "Upload record not listed")
    if not found:
        raise PilotAcceptanceError("uploaded fixture is not visible in project upload list")
    return file_id


def wait_for_analysis(session: PilotSession, project_id: str, timeout_seconds: int) -> str:
    key = f"pilot-{secrets.token_hex(12)}"
    status, payload, _ = session.request(
        "POST",
        f"/api/analysis/start/{project_id}",
        payload={"analysis_type": "all"},
        headers={"Idempotency-Key": key},
    )
    job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
    job_id = extract_id(job, "job_id", "id")
    session.record("start pilot analysis", status, ids={"job_id": short_id(job_id)}, message="Analysis job queued")
    if not job_id:
        raise PilotAcceptanceError("analysis start response did not contain job_id")

    deadline = time.monotonic() + timeout_seconds
    terminal = {"completed", "failed", "dead_lettered", "cancelled"}
    while time.monotonic() < deadline:
        time.sleep(3)
        status, payload, _ = session.request("GET", f"/api/analysis/jobs/{job_id}")
        job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
        job_status = str(job.get("status") or job.get("job_status") or "").lower()
        if status not in range(200, 300):
            session.record("poll analysis job", status, ids={"job_id": short_id(job_id)}, message="Job polling failed")
        if job_status in terminal:
            session.record(
                "analysis job completion",
                status,
                ids={"job_id": short_id(job_id)},
                message=f"Analysis job reached {job_status or 'unknown'}",
            )
            if job_status != "completed":
                raise PilotAcceptanceError(f"analysis did not complete successfully: {job_status or 'unknown'}")
            break
    else:
        raise PilotAcceptanceError(f"analysis job did not finish within {timeout_seconds} seconds")

    status, payload, _ = session.request("GET", f"/api/analysis/results/{project_id}")
    result = payload.get("analysis_result") if isinstance(payload.get("analysis_result"), dict) else {}
    session.record("analysis result available", status, ids={"job_id": short_id(job_id)}, message="Analysis result retrieved" if result else "Analysis result payload empty")
    if not result:
        raise PilotAcceptanceError("completed job did not expose an analysis result")
    return job_id


def generate_report(session: PilotSession, project_id: str) -> str:
    status, payload, _ = session.request(
        "POST",
        f"/api/reports/generate/{project_id}",
        payload={"report_format": "pdf", "report_type": "Pilot acceptance report"},
    )
    report = payload.get("report") if isinstance(payload.get("report"), dict) else payload
    report_id = extract_id(report, "report_id", "id")
    session.record("generate pilot report", status, ids={"report_id": short_id(report_id)}, message="Frozen report generated")
    if not report_id:
        raise PilotAcceptanceError("report generation response did not contain report_id")
    status, _, _ = session.request("GET", f"/api/reports/{report_id}/download", timeout=60)
    session.record("download pilot report", status, ids={"report_id": short_id(report_id)}, message="Report download returned")
    return report_id


def cleanup(session: PilotSession, project_id: str, file_id: str = "") -> None:
    if file_id:
        status, _, _ = session.request("DELETE", f"/api/uploads/{file_id}")
        session.record("cleanup upload", status, expected={200, 204}, ids={"file_id": short_id(file_id)}, message="Pilot upload cleanup requested")
    status, _, _ = session.request("DELETE", f"/api/projects/{project_id}")
    session.record("cleanup project", status, expected={200, 204}, ids={"project_id": short_id(project_id)}, message="Pilot project cleanup requested")


def write_evidence(path: Path, session: PilotSession, outcome: str, error: str = "") -> None:
    payload = {
        "schema_version": "1.0",
        "tool": "pilot_acceptance",
        "outcome": outcome,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontend": safe_url(session.frontend),
        "backend": safe_url(session.backend),
        "evidence": [item.as_dict() for item in session.evidence],
    }
    if error:
        payload["error"] = error
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run guarded production-pilot acceptance checks for DevBareun.")
    parser.add_argument("--frontend-url", required=True, help="Frontend base URL, for example https://devbareun.com")
    parser.add_argument("--backend-url", required=True, help="Backend base URL, for example https://api.example.com")
    parser.add_argument("--access-token-env", default="DEVBAREUN_E2E_ACCESS_TOKEN", help="Environment variable holding a short-lived Supabase access token")
    parser.add_argument("--login-email", help="Optional dedicated pilot account email; password is read only from --password-env")
    parser.add_argument("--password-env", default="DEVBAREUN_E2E_PASSWORD", help="Environment variable holding the pilot account password")
    parser.add_argument("--strict", action="store_true", help="Fail when the deployed readiness payload is not production-ready")
    parser.add_argument("--write", action="store_true", help="Create a dedicated pilot project and upload a deterministic CSV fixture")
    parser.add_argument("--confirm-write", default="", help=f"Required with --write: {WRITE_CONFIRMATION}")
    parser.add_argument("--run-analysis", action="store_true", help="Start analysis; this can consume a plan credit")
    parser.add_argument("--confirm-analysis", default="", help=f"Required with --run-analysis: {ANALYSIS_CONFIRMATION}")
    parser.add_argument("--generate-report", action="store_true", help="Generate and download a frozen PDF report after analysis")
    parser.add_argument("--confirm-report", default="", help=f"Required with --generate-report: {REPORT_CONFIRMATION}")
    parser.add_argument("--analysis-timeout", type=int, default=240, help="Maximum seconds to wait for analysis completion")
    parser.add_argument("--cleanup", action="store_true", help="Delete the fixture upload and pilot project at the end")
    parser.add_argument("--project-name", default="", help="Optional exact pilot project name")
    parser.add_argument("--output", type=Path, help="Optional redacted JSON evidence output path")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    require_confirmation(args.write, args.confirm_write, WRITE_CONFIRMATION, "write")
    if args.run_analysis and not args.write:
        raise PilotAcceptanceError("--run-analysis requires --write")
    require_confirmation(args.run_analysis, args.confirm_analysis, ANALYSIS_CONFIRMATION, "analysis")
    if args.generate_report and not args.run_analysis:
        raise PilotAcceptanceError("--generate-report requires --run-analysis")
    require_confirmation(args.generate_report, args.confirm_report, REPORT_CONFIRMATION, "report")
    if args.analysis_timeout < 30 or args.analysis_timeout > 3600:
        raise PilotAcceptanceError("--analysis-timeout must be between 30 and 3600 seconds")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    session = PilotSession(backend=args.backend_url, frontend=args.frontend_url)
    outcome = "failed"
    error = ""
    project_id = ""
    file_id = ""
    try:
        validate_args(args)
        public_checks(session, strict=args.strict)
        init_csrf(session)
        authenticate(session, args)
        if args.write:
            suffix = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            project_id = args.project_name.strip() or f"DevBareun Pilot Acceptance {suffix}"
            project_id = create_project(session, project_id)
            file_id = upload_fixture(session, project_id)
            if args.run_analysis:
                wait_for_analysis(session, project_id, args.analysis_timeout)
            if args.generate_report:
                generate_report(session, project_id)
            if args.cleanup:
                cleanup(session, project_id, file_id)
        outcome = "passed"
        print("Pilot acceptance passed.")
        return 0
    except PilotAcceptanceError as exc:
        error = str(exc)
        print(f"Pilot acceptance failed: {error}", file=sys.stderr)
        return 1
    finally:
        if args.output:
            write_evidence(args.output, session, outcome, error)


if __name__ == "__main__":
    raise SystemExit(main())
