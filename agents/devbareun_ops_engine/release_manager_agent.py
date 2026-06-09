from __future__ import annotations

import json
import re
from datetime import datetime
from .agent_base import BaseAgent


class ReleaseManagerAgent(BaseAgent):
    name = "ReleaseManagerAgent"
    description = "Checks version markers and prepares release notes."

    def check(self) -> None:
        version = "1.1.3-fixed-release"
        candidates = [
            self.backend_root / "app" / "main.py",
            self.root / "agents" / "devbareun_ops_engine" / "__init__.py",
        ]
        found = []
        for path in candidates:
            if path.exists():
                text = self.read(path)
                if version in text:
                    found.append(str(path))
        notes = {
            "version": version,
            "date": datetime.utcnow().date().isoformat(),
            "summary": "Adds DevBareun Ops Engine with QA, site management, deployment readiness, SEO, security, browser QA, parser accuracy, marketing research and supervisor reporting agents.",
            "manual_approval_required_for": [
                "production deploy",
                "payment provider logic changes",
                "database deletion or migration",
                "domain/DNS changes",
                "secret/token changes",
            ],
        }
        out = self.out_dir / "release_notes_v1_1_3_fixed_release.json"
        out.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
        if not found:
            self.add("info", "Version marker not found in code yet.", recommendation="Set package/release marker to 1.1.3-fixed-release after merge.")
        self.metrics["release_notes"] = notes
