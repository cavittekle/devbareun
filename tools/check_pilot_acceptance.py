#!/usr/bin/env python3
"""Static contract check for guarded production pilot acceptance tooling."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

TOOL_PATH = Path("tools/pilot_acceptance.py")
DOC_PATH = Path("docs/PILOT_ACCEPTANCE_V1427.md")
RUNBOOK_PATH = Path("docs/PRODUCTION_DEPLOYMENT_RUNBOOK_V1414.md")
CI_PATH = Path(".github/workflows/ci.yml")

REQUIRED_TOOL_MARKERS = (
    "WRITE_CONFIRMATION = \"PILOT_WRITE\"",
    "ANALYSIS_CONFIRMATION = \"PILOT_ANALYSIS\"",
    "REPORT_CONFIRMATION = \"PILOT_REPORT\"",
    "--write",
    "--run-analysis",
    "--generate-report",
    "--cleanup",
    "--access-token-env",
    "include_session_auth=False",
    "safe_url",
    "write_evidence",
)

REQUIRED_DOC_MARKERS = (
    "dedicated pilot customer account",
    "read-only",
    "PILOT_WRITE",
    "PILOT_ANALYSIS",
    "PILOT_REPORT",
    "DEVBAREUN_E2E_ACCESS_TOKEN",
    "does not create a payment checkout",
    "not executed against a live URL in CI",
)


@dataclass
class Result:
    errors: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check(root: Path) -> Result:
    result = Result(errors=[])
    for path in (TOOL_PATH, DOC_PATH, RUNBOOK_PATH, CI_PATH):
        if not (root / path).exists():
            result.errors.append(f"missing pilot acceptance contract file: {path.as_posix()}")
    if result.errors:
        return result

    source = read(root / TOOL_PATH)
    for marker in REQUIRED_TOOL_MARKERS:
        if marker not in source:
            result.errors.append(f"pilot acceptance tool missing safety marker: {marker}")
    for forbidden in ("print(access_token", "print(self.access_token", "print(password", "print(csrf"):
        if forbidden in source.replace(" ", ""):
            result.errors.append(f"pilot acceptance tool may print sensitive material: {forbidden}")

    docs = read(root / DOC_PATH).lower()
    for marker in REQUIRED_DOC_MARKERS:
        if marker.lower() not in docs:
            result.errors.append(f"pilot acceptance documentation missing marker: {marker}")

    runbook = read(root / RUNBOOK_PATH)
    if "tools/pilot_acceptance.py" not in runbook:
        result.errors.append("production runbook does not link pilot acceptance tool")
    ci = read(root / CI_PATH)
    if "tools/check_pilot_acceptance.py" not in ci:
        result.errors.append("CI does not run pilot acceptance contract checker")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check guarded DevBareun pilot acceptance tooling.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.root.resolve())
    payload = {"ok": result.ok, "errors": result.errors}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Pilot acceptance contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
