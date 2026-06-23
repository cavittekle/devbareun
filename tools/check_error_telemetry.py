#!/usr/bin/env python3
"""Static contract for DevBareun v1.4.28 privacy-safe error telemetry."""
from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

FILES = {
    "telemetry": Path("backend/app/telemetry.py"),
    "main": Path("backend/app/main.py"),
    "analysis_worker": Path("backend/app/analysis_worker.py"),
    "archive_worker": Path("backend/app/audit_archive_worker.py"),
    "operations": Path("backend/app/services/operations_health_service.py"),
    "env_validator": Path("tools/validate_production_env.py"),
    "provider_checker": Path("tools/check_provider_config.py"),
    "web_template": Path("deploy/env/railway-web.env.template"),
    "worker_template": Path("deploy/env/railway-worker.env.template"),
    "archive_template": Path("deploy/env/railway-audit-archive.env.template"),
    "doc": Path("docs/ERROR_TELEMETRY_V1428.md"),
    "ci": Path(".github/workflows/ci.yml"),
}

@dataclass
class Result:
    errors: List[str] = field(default_factory=list)


def read(root: Path, name: str, result: Result) -> str:
    path = root / FILES[name]
    if not path.exists():
        result.errors.append(f"missing required file: {path.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result()
    source = {name: read(root, name, result) for name in FILES}
    for phrase in ("sanitize_metadata", "capture_exception", "DEVBAREUN_ERROR_TELEMETRY_MODE", "DEVBAREUN_SENTRY_DSN", "default_integrations=False", "capture_message"):
        if phrase not in source["telemetry"]:
            result.errors.append(f"telemetry module missing: {phrase}")
    for phrase in ("configure_telemetry", "api_unhandled_exception", "api_request_completed", "X-Request-ID"):
        if phrase not in source["main"]:
            result.errors.append(f"main telemetry integration missing: {phrase}")
    for name in ("analysis_worker", "archive_worker"):
        for phrase in ("configure_telemetry", "capture_exception"):
            if phrase not in source[name]:
                result.errors.append(f"{name} telemetry integration missing: {phrase}")
    for phrase in ("error_telemetry_status", "_telemetry_component", "error_telemetry_not_configured"):
        if phrase not in source["operations"]:
            result.errors.append(f"operations telemetry health missing: {phrase}")
    for name in ("env_validator", "provider_checker", "web_template", "worker_template", "archive_template"):
        for phrase in ("DEVBAREUN_ERROR_TELEMETRY_MODE", "DEVBAREUN_REQUIRE_ERROR_TELEMETRY", "DEVBAREUN_SENTRY_DSN"):
            if phrase not in source[name]:
                result.errors.append(f"{name} missing telemetry env key: {phrase}")
    for phrase in ("sanitized", "Sentry", "request_id", "DEVBAREUN_SENTRY_DSN"):
        if phrase.lower() not in source["doc"].lower():
            result.errors.append(f"telemetry documentation missing: {phrase}")
    if "tools/check_error_telemetry.py" not in source["ci"]:
        result.errors.append("CI does not run tools/check_error_telemetry.py")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun error telemetry contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = check(args.root.resolve())
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Error telemetry contract {'passed' if not result.errors else 'failed'}: {len(result.errors)} error(s).")
    return 0 if not result.errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
