#!/usr/bin/env python3
"""Export and check the DevBareun FastAPI route contract.

This tool intentionally uses the application object instead of scraping docs from
an already deployed server. It catches accidental route removals, duplicate
method/path registrations and legacy endpoint re-exposure before deployment.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REQUIRED_ROUTES: Tuple[Tuple[str, str], ...] = (
    ("GET", "/api/health"),
    ("GET", "/api/readiness"),
    ("GET", "/api/version"),
    ("GET", "/api/auth/csrf"),
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/supabase/login"),
    ("POST", "/api/auth/supabase/register"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/projects/list"),
    ("POST", "/api/projects/create"),
    ("GET", "/api/projects/{project_id}"),
    ("PATCH", "/api/projects/{project_id}"),
    ("DELETE", "/api/projects/{project_id}"),
    ("POST", "/api/uploads/create-url"),
    ("POST", "/api/uploads/mark-uploaded"),
    ("GET", "/api/uploads/project/{project_id}"),
    ("DELETE", "/api/uploads/{file_id}"),
    ("POST", "/api/analysis/start/{project_id}"),
    ("GET", "/api/analysis/jobs/{job_id}"),
    ("GET", "/api/analysis/results/{project_id}"),
    ("GET", "/api/operations/health"),
    ("GET", "/api/dashboard/executive/{project_id}"),
    ("GET", "/api/dashboard/portfolio"),
    ("GET", "/api/reports/project/{project_id}"),
    ("POST", "/api/reports/generate/{project_id}"),
    ("GET", "/api/reports/{report_id}/download"),
    ("GET", "/api/credits/status"),
    ("GET", "/api/subscriptions/status"),
    ("GET", "/api/billing/status"),
    ("GET", "/api/billing/usage"),
    ("GET", "/api/billing/checkouts/{checkout_id}"),
    ("POST", "/api/billing/create-one-time-checkout"),
    ("POST", "/api/billing/create-subscription-checkout"),
    ("POST", "/api/billing/webhook"),
    ("GET", "/api/guest-result/{token}"),
    ("GET", "/api/privacy/policy"),
    ("GET", "/api/privacy/requests"),
    ("POST", "/api/privacy/export-requests"),
    ("POST", "/api/privacy/erasure-requests"),
    ("POST", "/api/privacy/requests/{request_id}/cancel"),
    ("GET", "/api/admin/data-lifecycle/requests"),
    ("PATCH", "/api/admin/data-lifecycle/requests/{request_id}"),
    ("GET", "/api/super-admin/data-lifecycle/requests"),
    ("PATCH", "/api/super-admin/data-lifecycle/requests/{request_id}"),
    ("GET", "/api/admin/audit-integrity"),
    ("GET", "/api/super-admin/audit-integrity"),
    ("GET", "/api/admin/operations-health"),
    ("GET", "/api/super-admin/operations-health"),
)

LEGACY_PROJECT_ROUTES: Tuple[Tuple[str, str], ...] = (
    ("POST", "/api/projects"),
    ("POST", "/api/projects/{project_id}/upload"),
    ("POST", "/api/projects/{project_id}/preflight"),
    ("POST", "/api/projects/{project_id}/analyze"),
    ("GET", "/api/projects/{project_id}/dashboard"),
    ("GET", "/api/projects/{project_id}/report/pdf"),
    ("GET", "/api/projects/{project_id}/report/excel"),
    ("POST", "/api/payments/create-checkout"),
)

FORBIDDEN_REACT_ENDPOINT_SNIPPETS = (
    "/api/analysis/create",
    "/api/workspace/guest-results",
    "/api/projects/{project_id}/upload",
    "/api/projects/" + "${projectId}" + "/upload",
)

IGNORED_DUPLICATE_PATHS = {
    # Swagger/ReDoc helper routes can legitimately add multiple methods/aliases.
    ("GET", "/docs"),
    ("HEAD", "/docs"),
    ("GET", "/redoc"),
    ("HEAD", "/redoc"),
    ("GET", "/openapi.json"),
    ("HEAD", "/openapi.json"),
}


@dataclass
class ContractResult:
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _prepare_import(root: Path) -> None:
    backend_root = root / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    os.environ.setdefault("DEVBAREUN_PRODUCTION_SECURITY", "false")
    os.environ.setdefault("DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT", "true")
    os.environ.setdefault("DEVBAREUN_EXPOSE_LEGACY_PROJECT_ROUTES", "false")


def _load_app(root: Path):
    _prepare_import(root)
    return importlib.import_module("app.main").app


def route_manifest(root: Path) -> Dict[str, object]:
    app = _load_app(root)
    version = getattr(importlib.import_module("app.version"), "APP_VERSION", "unknown")
    routes: List[Dict[str, object]] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path:
            continue
        methods = sorted((getattr(route, "methods", None) or []))
        for method in methods:
            routes.append(
                {
                    "method": method,
                    "path": path,
                    "name": getattr(route, "name", ""),
                    "include_in_schema": bool(getattr(route, "include_in_schema", False)),
                    "tags": list(getattr(route, "tags", []) or []),
                }
            )
    routes.sort(key=lambda item: (str(item["path"]), str(item["method"]), str(item["name"])))
    return {
        "service": "DevBareun Backend",
        "version": version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "route_count": len(routes),
        "required_routes": [{"method": method, "path": path} for method, path in REQUIRED_ROUTES],
        "legacy_project_routes": [{"method": method, "path": path} for method, path in LEGACY_PROJECT_ROUTES],
        "routes": routes,
    }


def _route_keys(manifest: Dict[str, object], schema_only: bool | None = None) -> List[Tuple[str, str]]:
    keys: List[Tuple[str, str]] = []
    for route in manifest.get("routes", []):
        if not isinstance(route, dict):
            continue
        if schema_only is not None and bool(route.get("include_in_schema")) != schema_only:
            continue
        method = str(route.get("method") or "")
        path = str(route.get("path") or "")
        if method and path:
            keys.append((method, path))
    return keys


def _scan_react_client(root: Path) -> List[str]:
    src_root = root / "frontend" / "member-dashboard-app" / "src"
    if not src_root.exists():
        return ["React workspace source directory is missing."]
    errors: List[str] = []
    for path in src_root.rglob("*"):
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        for snippet in FORBIDDEN_REACT_ENDPOINT_SNIPPETS:
            if snippet in source:
                errors.append(f"React workspace still references deprecated endpoint {snippet!r} in {path.relative_to(root).as_posix()}")
    return errors


def check_contract(root: Path) -> ContractResult:
    manifest = route_manifest(root)
    errors: List[str] = []
    warnings: List[str] = []
    all_keys = set(_route_keys(manifest))
    schema_keys = set(_route_keys(manifest, schema_only=True))

    for method, path in REQUIRED_ROUTES:
        if (method, path) not in all_keys:
            errors.append(f"required route is missing: {method} {path}")

    for method, path in LEGACY_PROJECT_ROUTES:
        if (method, path) in schema_keys:
            errors.append(f"legacy route is exposed in OpenAPI: {method} {path}")
        elif (method, path) not in all_keys:
            warnings.append(f"legacy compatibility route is absent instead of disabled: {method} {path}")

    occurrences: Dict[Tuple[str, str], List[str]] = {}
    for route in manifest.get("routes", []):
        if not isinstance(route, dict):
            continue
        key = (str(route.get("method") or ""), str(route.get("path") or ""))
        if key in IGNORED_DUPLICATE_PATHS:
            continue
        occurrences.setdefault(key, []).append(str(route.get("name") or ""))
    for (method, path), names in sorted(occurrences.items()):
        if len(names) > 1:
            errors.append(f"duplicate route registration: {method} {path} -> {', '.join(names)}")

    errors.extend(_scan_react_client(root))
    return ContractResult(errors=errors, warnings=warnings)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export/check the DevBareun API contract.")
    parser.add_argument("--root", type=Path, default=_repo_root(), help="Repository root.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path for the route manifest.")
    parser.add_argument("--check", action="store_true", help="Fail if required routes, duplicate routes or frontend endpoint constraints are violated.")
    parser.add_argument("--json", action="store_true", help="Print check result as JSON.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    manifest = route_manifest(root)
    if args.output:
        write_json(args.output.resolve(), manifest)

    result = check_contract(root) if args.check else ContractResult(errors=[], warnings=[])
    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings, "route_count": manifest.get("route_count")}, indent=2))
    else:
        if args.output:
            print(f"Wrote API contract manifest: {args.output.resolve()}")
        if args.check:
            for warning in result.warnings:
                print(f"[WARN] {warning}")
            for error in result.errors:
                print(f"[FAIL] {error}")
            print(f"API contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
        elif not args.output:
            print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

# v1.4.33 explicit project-sharing routes are validated by tools/check_project_sharing.py.
