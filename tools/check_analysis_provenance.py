#!/usr/bin/env python3
"""Static contract checks for DevBareun analysis input provenance v1.4.22."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence


MIGRATION = Path("database/2026_06_19_v1422_analysis_input_provenance.sql")
DOC = Path("docs/ANALYSIS_INPUT_PROVENANCE_V1422.md")
PROVENANCE_MODULE = Path("backend/app/services/analysis_provenance.py")
JOB_SERVICE = Path("backend/app/services/analysis_job_service.py")
DASHBOARD_SERVICE = Path("backend/app/services/dashboard_service.py")
REPORT_SERVICE = Path("backend/app/services/report_service.py")
RESULT_VIEWER = Path("frontend/member-dashboard-app/src/pages/ResultViewer.jsx")
CI = Path(".github/workflows/ci.yml")
DEPLOY_ORDER = Path("database/SUPABASE_DEPLOY_ORDER.md")


@dataclass
class Result:
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def text(root: Path, rel: Path, result: Result) -> str:
    path = root / rel
    if not path.exists():
        result.errors.append(f"missing required file: {rel.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result()
    migration = text(root, MIGRATION, result)
    docs = text(root, DOC, result)
    provenance = text(root, PROVENANCE_MODULE, result)
    jobs = text(root, JOB_SERVICE, result)
    dashboard = text(root, DASHBOARD_SERVICE, result)
    reports = text(root, REPORT_SERVICE, result)
    viewer = text(root, RESULT_VIEWER, result)
    ci = text(root, CI, result)
    deploy_order = text(root, DEPLOY_ORDER, result)

    for phrase in ("input_manifest", "input_manifest_sha256", "input_file_count", "provenance_schema_version"):
        if phrase not in migration:
            result.errors.append(f"migration missing {phrase}")
    for phrase in ("build_analysis_input_manifest", "source_fingerprint", "storage paths", "signed URLs"):
        if phrase.lower() not in provenance.lower():
            result.errors.append(f"provenance module missing required privacy/integrity behavior: {phrase}")
    for phrase in ("build_analysis_input_manifest", "_provenance_patch", "input_manifest=input_manifest"):
        if phrase not in jobs:
            result.errors.append(f"analysis job service missing provenance persistence: {phrase}")
    if "analysis_provenance" not in dashboard:
        result.errors.append("executive dashboard does not expose analysis provenance")
    if "analysis_provenance" not in reports:
        result.errors.append("frozen report payload does not retain analysis provenance")
    for phrase in ("InputProvenance", "Analysis source traceability", "source_fingerprint"):
        if phrase not in viewer:
            result.errors.append(f"workspace result viewer missing provenance UI: {phrase}")
    if MIGRATION.name not in deploy_order:
        result.errors.append("deploy order does not include v1.4.22 provenance migration")
    if "tools/check_analysis_provenance.py" not in ci:
        result.errors.append("CI does not run analysis provenance contract checker")
    for phrase in ("immutable", "storage", "signed", "checksum", "not a security scanner"):
        if phrase not in docs.lower():
            result.errors.append(f"provenance documentation missing required explanation: {phrase}")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check v1.4.22 analysis-input provenance contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.root.resolve())
    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors}, indent=2))
    else:
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Analysis provenance contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
