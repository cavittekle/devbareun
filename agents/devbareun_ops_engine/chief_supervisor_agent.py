from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from .agent_base import AgentResult, STATUS_FAIL, STATUS_PASS, STATUS_WARN


class ChiefSupervisorAgent:
    """Controls all agents, grades system health and writes management reports."""

    def __init__(self, root: Path, out_dir: Path):
        self.root = Path(root).resolve()
        self.out_dir = Path(out_dir).resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def grade(self, results: Iterable[AgentResult]) -> Dict[str, Any]:
        results = list(results)
        total = len(results) or 1
        avg_score = round(sum(r.score for r in results) / total, 1)
        fail_count = sum(1 for r in results if r.status == STATUS_FAIL)
        warn_count = sum(1 for r in results if r.status == STATUS_WARN)
        pass_count = sum(1 for r in results if r.status == STATUS_PASS)
        if fail_count:
            decision = "BLOCK_RELEASE"
        elif warn_count:
            decision = "REVIEW_BEFORE_RELEASE"
        else:
            decision = "READY_FOR_RELEASE"
        return {
            "decision": decision,
            "average_score": avg_score,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "agent_count": total,
        }

    def write_reports(self, results: List[AgentResult]) -> Dict[str, Path]:
        grade = self.grade(results)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "supervisor": "ChiefSupervisorAgent",
            "grade": grade,
            "results": [r.to_dict() for r in results],
        }
        json_path = self.out_dir / "agentops_supervisor_report.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        md = [
            "# DevBareun AgentOps Supervisor Report",
            "",
            f"Generated: `{payload['generated_at']}`",
            "",
            f"## Decision: `{grade['decision']}`",
            "",
            f"- Average score: **{grade['average_score']}**",
            f"- Passed: **{grade['pass_count']}**",
            f"- Warnings: **{grade['warn_count']}**",
            f"- Failed: **{grade['fail_count']}**",
            "",
            "## Agent Results",
            "",
            "| Agent | Status | Score | Summary |",
            "|---|---:|---:|---|",
        ]
        for r in results:
            md.append(f"| {r.agent} | {r.status} | {r.score} | {r.summary.replace('|','/')} |")
        md += ["", "## Findings", ""]
        for r in results:
            if not r.findings:
                continue
            md.append(f"### {r.agent}")
            for f in r.findings:
                loc = f" `{f.file}`" if f.file else ""
                line = f":{f.line}" if f.line else ""
                rec = f" Recommendation: {f.recommendation}" if f.recommendation else ""
                md.append(f"- **{f.severity}**{loc}{line}: {f.message}.{rec}")
            md.append("")
        md_path = self.out_dir / "agentops_supervisor_report.md"
        md_path.write_text("\n".join(md), encoding="utf-8")
        return {"json": json_path, "markdown": md_path}
