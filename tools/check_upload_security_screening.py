#!/usr/bin/env python3
"""Static contract checks for DevBareun upload-security screening v1.4.21."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence


MIGRATION = Path("database/2026_06_19_v1421_upload_security_screening.sql")
DOC = Path("docs/UPLOAD_SECURITY_SCREENING_V1421.md")
PARSER_SERVICE = Path("backend/app/services/parser_service.py")
SCREENING_MODULE = Path("backend/app/upload_security.py")
JOB_SERVICE = Path("backend/app/services/analysis_job_service.py")
CI = Path(".github/workflows/ci.yml")
DEPLOY_ORDER = Path("database/SUPABASE_DEPLOY_ORDER.md")
ENV_TEMPLATES = (
    Path("backend/.env.example"),
    Path("deploy/env/railway-web.env.template"),
    Path("deploy/env/railway-worker.env.template"),
)
REQUIRED_ENV_KEYS = (
    "DEVBAREUN_MAX_OFFICE_ARCHIVE_ENTRIES",
    "DEVBAREUN_MAX_OFFICE_UNCOMPRESSED_BYTES",
    "DEVBAREUN_MAX_OFFICE_COMPRESSION_RATIO",
    "DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS",
    "DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT",
)


@dataclass
class Result:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

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
    parser_service = text(root, PARSER_SERVICE, result)
    screening = text(root, SCREENING_MODULE, result)
    jobs = text(root, JOB_SERVICE, result)
    ci = text(root, CI, result)
    deploy_order = text(root, DEPLOY_ORDER, result)

    for phrase in (
        "security_scan_status",
        "security_scan_findings",
        "quarantine_status",
        "quarantined_at",
    ):
        if phrase not in migration:
            result.errors.append(f"migration missing {phrase}")
    for phrase in ("screen_materialized_upload", "UploadSecurityScreeningError", "office_archive"):
        if phrase not in screening:
            result.errors.append(f"screening module missing {phrase}")
    if "screen_materialized_upload" not in parser_service:
        result.errors.append("parser service does not call security screening before parser execution")
    for phrase in ("security_scan_status", "quarantine_status", "security_scan_findings"):
        if phrase not in jobs:
            result.errors.append(f"analysis job persistence/filtering missing {phrase}")
    if MIGRATION.name not in deploy_order:
        result.errors.append("deploy order does not include v1.4.21 migration")
    if "tools/check_upload_security_screening.py" not in ci:
        result.errors.append("CI does not run upload security screening contract checker")
    for phrase in ("not an antivirus", "quarantine", "macro", "PDF"):
        if phrase.lower() not in docs.lower():
            result.errors.append(f"screening documentation missing required explanation: {phrase}")
    for template in ENV_TEMPLATES:
        source = text(root, template, result)
        for key in REQUIRED_ENV_KEYS:
            if key not in source:
                result.errors.append(f"{template.as_posix()} missing {key}")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check v1.4.21 upload-security screening contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.root.resolve())
    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, indent=2))
    else:
        for warning in result.warnings:
            print(f"[WARN] {warning}")
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Upload security screening contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
