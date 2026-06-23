#!/usr/bin/env python3
"""HTTP smoke tests for a deployed DevBareun frontend/backend pair.

The script uses only the Python standard library. It does not log secrets and it
only checks public health/readiness pages and the public CSRF initializer.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    label: str
    ok: bool
    status: int | None = None
    message: str = ""
    body: str = ""


def normalize_base(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    return value.rstrip("/") + "/"


def fetch(url: str, timeout: int = 15) -> Tuple[int | None, str, str]:
    req = Request(url, headers={"User-Agent": "DevBareunSmoke/1.4.8"})
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read(1024 * 512).decode("utf-8", errors="replace")
            return response.status, body, ""
    except HTTPError as exc:
        body = exc.read(1024 * 128).decode("utf-8", errors="replace")
        return exc.code, body, str(exc)
    except URLError as exc:
        return None, "", str(exc.reason)
    except Exception as exc:  # pragma: no cover - smoke script resilience
        return None, "", str(exc)


def check_http(label: str, url: str, expected: range = range(200, 400)) -> CheckResult:
    status, body, error = fetch(url)
    ok = status in expected if status is not None else False
    message = f"HTTP {status}" if status is not None else error
    return CheckResult(label=label, ok=ok, status=status, message=message, body=body)


def parse_json(body: str) -> Dict[str, Any]:
    try:
        data = json.loads(body)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def readiness_findings(readiness: Dict[str, Any], strict: bool) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if not readiness:
        warnings.append("backend readiness payload is missing")
        return errors, warnings

    if readiness.get("production_security") is not True:
        errors.append("production_security is not true")
    for flag in ("dev_auth", "local_store", "mock_payment", "pilot_login", "pilot_checkout", "legacy_project_routes", "ephemeral_upload"):
        if readiness.get(flag) != "disabled":
            errors.append(f"{flag} is {readiness.get(flag)}")
    if readiness.get("csrf_token") != "required":
        errors.append("csrf_token is not required")
    if readiness.get("docs") != "disabled":
        warnings.append("docs are enabled")
    if readiness.get("analysis_job_mode") != "worker":
        warnings.append("analysis_job_mode is not worker")
    if readiness.get("rate_limit") != "upstash":
        message = "rate_limit is not upstash"
        (errors if strict else warnings).append(message)
    if readiness.get("supabase_private") != "configured":
        message = "supabase_private is not configured"
        (errors if strict else warnings).append(message)
    if readiness.get("lemonsqueezy") != "configured":
        message = "lemonsqueezy is not configured"
        (errors if strict else warnings).append(message)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test deployed DevBareun services.")
    parser.add_argument("--frontend-url", required=True, help="Frontend base URL, e.g. https://devbareun.com")
    parser.add_argument("--backend-url", required=True, help="Backend base URL, e.g. https://devbareun-production.up.railway.app")
    parser.add_argument("--strict", action="store_true", help="Treat provider readiness warnings as failures.")
    parser.add_argument("--retries", type=int, default=1, help="Retries per check for cold starts.")
    args = parser.parse_args()

    frontend = normalize_base(args.frontend_url)
    backend = normalize_base(args.backend_url)
    checks = [
        ("frontend index", urljoin(frontend, "index.html")),
        ("workspace shell", urljoin(frontend, "workspace/")),
        ("backend health", urljoin(backend, "api/health")),
        ("backend readiness", urljoin(backend, "api/readiness")),
        ("backend version", urljoin(backend, "api/version")),
        ("csrf initializer", urljoin(backend, "api/auth/csrf")),
    ]

    results: List[CheckResult] = []
    for label, url in checks:
        result = None
        for attempt in range(max(args.retries, 1)):
            result = check_http(label, url)
            if result.ok:
                break
            if attempt + 1 < args.retries:
                time.sleep(2)
        assert result is not None
        results.append(result)

    failures = 0
    warnings: List[str] = []
    readiness_payload: Dict[str, Any] = {}
    for result in results:
        prefix = "[PASS]" if result.ok else "[FAIL]"
        print(f"{prefix} {result.label}: {result.message}")
        if not result.ok:
            failures += 1
        if result.label == "backend readiness":
            data = parse_json(result.body)
            readiness_payload = data.get("readiness") if isinstance(data.get("readiness"), dict) else {}
            for item in data.get("errors", []) if isinstance(data.get("errors"), list) else []:
                failures += 1
                print(f"[FAIL] readiness: {item}")
            for item in data.get("warnings", []) if isinstance(data.get("warnings"), list) else []:
                warnings.append(f"readiness: {item}")

    readiness_errors, readiness_warnings = readiness_findings(readiness_payload, args.strict)
    for item in readiness_errors:
        failures += 1
        print(f"[FAIL] readiness flag: {item}")
    warnings.extend(f"readiness flag: {item}" for item in readiness_warnings)
    for item in warnings:
        print(f"[WARN] {item}")

    if failures:
        print(f"Smoke test failed: {failures} failure(s), {len(warnings)} warning(s).")
        return 1
    print(f"Smoke test passed: {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
