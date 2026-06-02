from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import traceback
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"


@dataclass
class Finding:
    severity: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentResult:
    agent: str
    status: str
    started_at: str
    duration_seconds: float
    score: int = 100
    summary: str = ""
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == STATUS_PASS

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["passed"] = self.passed
        data["findings"] = [f.to_dict() for f in self.findings]
        return data


class BaseAgent:
    name = "BaseAgent"
    description = "Base DevBareun agent"

    def __init__(self, root: Path, frontend_root: Optional[Path] = None, backend_root: Optional[Path] = None, out_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        self.root = Path(root).resolve()
        self.frontend_root = Path(frontend_root or self.root / "frontend").resolve()
        self.backend_root = Path(backend_root or self.root / "backend").resolve()
        self.out_dir = Path(out_dir or self.root / "agent_reports").resolve()
        self.config = config or {}
        self.findings: List[Finding] = []
        self.metrics: Dict[str, Any] = {}

    def add(self, severity: str, message: str, file: Optional[Path | str] = None, line: Optional[int] = None, recommendation: Optional[str] = None) -> None:
        f = str(file) if file is not None else None
        if f:
            try:
                f = str(Path(f).resolve().relative_to(self.root))
            except Exception:
                pass
        self.findings.append(Finding(severity=severity, message=message, file=f, line=line, recommendation=recommendation))

    def run(self) -> AgentResult:
        started = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self.check()
        except Exception as exc:
            self.add("critical", f"Agent crashed: {exc}", recommendation=traceback.format_exc(limit=6))
        status, score = self._status_and_score()
        return AgentResult(
            agent=self.name,
            status=status,
            started_at=started_at,
            duration_seconds=round(time.time() - started, 3),
            score=score,
            summary=self.summary(),
            findings=self.findings,
            metrics=self.metrics,
        )

    def check(self) -> None:
        raise NotImplementedError

    def summary(self) -> str:
        if not self.findings:
            return "No issues detected."
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))

    def _status_and_score(self) -> tuple[str, int]:
        score = 100
        has_fail = False
        has_warn = False
        for f in self.findings:
            sev = f.severity.lower()
            if sev in {"critical", "error", "fail"}:
                has_fail = True
                score -= 35
            elif sev in {"warning", "warn"}:
                has_warn = True
                score -= 12
            elif sev in {"info", "note"}:
                score -= 2
        score = max(0, min(100, score))
        if has_fail:
            return STATUS_FAIL, score
        if has_warn:
            return STATUS_WARN, score
        return STATUS_PASS, score

    def iter_files(self, base: Path, patterns: Iterable[str]) -> Iterable[Path]:
        if not base.exists():
            return []
        files: List[Path] = []
        for pattern in patterns:
            files.extend(base.rglob(pattern))
        excluded = {".git", "node_modules", ".venv", "__pycache__", "agent_reports", "storage", "data"}
        return [p for p in files if not any(part in excluded for part in p.parts)]

    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def run_cmd(self, cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=str(cwd or self.root), text=True, capture_output=True, timeout=timeout)

    def http_get(self, url: str, timeout: int = 12) -> tuple[int, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "DevBareun-Ops-Engine/1.1"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read(200000).decode("utf-8", errors="ignore")
            return int(res.status), body


def load_config(root: Path, explicit: Optional[str] = None) -> Dict[str, Any]:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates += [Path(root) / "agents" / "devbareun_ops_engine" / "agentops.config.json", Path(root) / "agentops.config.json"]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}
