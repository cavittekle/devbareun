#!/usr/bin/env python3
"""Static release contract for DevBareun v1.4.29 backup and recovery controls."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

FILES = {
    "tool": Path("tools/backup_recovery.py"),
    "operator_template": Path("deploy/env/backup-operator.env.template"),
    "web_template": Path("deploy/env/railway-web.env.template"),
    "worker_template": Path("deploy/env/railway-worker.env.template"),
    "archive_template": Path("deploy/env/railway-audit-archive.env.template"),
    "env_validator": Path("tools/validate_production_env.py"),
    "provider_checker": Path("tools/check_provider_config.py"),
    "runbook": Path("docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md"),
    "doc": Path("docs/BACKUP_AND_RECOVERY_V1429.md"),
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
    for phrase in ("database-backup", "storage-manifest", "restore-preflight", "RUN_DATABASE_BACKUP", "RUN_STORAGE_MANIFEST", "RUN_RESTORE_PREFLIGHT", "isolated_environment_only", "pg_dump", "pg_restore"):
        if phrase not in source["tool"]:
            result.errors.append(f"backup operator tool missing: {phrase}")
    for phrase in ("DEVBAREUN_BACKUP_DATABASE_URL", "DEVBAREUN_BACKUP_OUTPUT_DIR", "DEVBAREUN_BACKUP_REQUIRED", "DEVBAREUN_BACKUP_RPO_HOURS", "DEVBAREUN_BACKUP_RTO_HOURS"):
        if phrase not in source["operator_template"]:
            result.errors.append(f"backup operator template missing: {phrase}")
    for name in ("web_template", "worker_template", "archive_template", "env_validator", "provider_checker"):
        for phrase in ("DEVBAREUN_BACKUP_REQUIRED", "DEVBAREUN_BACKUP_RPO_HOURS", "DEVBAREUN_BACKUP_RTO_HOURS", "DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS"):
            if phrase not in source[name]:
                result.errors.append(f"{name} missing backup policy key: {phrase}")
    for phrase in ("RPO", "RTO", "isolated", "pg_dump", "storage", "restore drill", "do not restore"):
        if phrase.lower() not in source["doc"].lower():
            result.errors.append(f"backup recovery documentation lacks: {phrase}")
    for phrase in ("backup", "restore", "RPO", "RTO"):
        if phrase.lower() not in source["runbook"].lower():
            result.errors.append(f"deployment runbook lacks: {phrase}")
    if "tools/check_backup_recovery.py" not in source["ci"]:
        result.errors.append("CI does not run backup recovery contract")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun backup/recovery contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = check(args.root.resolve())
    for error in result.errors:
        print(f"[FAIL] {error}")
    print(f"Backup/recovery contract {'passed' if not result.errors else 'failed'}: {len(result.errors)} error(s).")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
