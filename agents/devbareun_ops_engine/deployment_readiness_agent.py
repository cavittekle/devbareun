from __future__ import annotations

import os
from pathlib import Path
from .agent_base import BaseAgent


class DeploymentReadinessAgent(BaseAgent):
    name = "DeploymentReadinessAgent"
    description = "Verifies GitHub/Vercel/Railway CI/CD readiness without pushing production changes."

    LIVE_QA_ENV = ["SITE_URL", "API_URL"]
    OPTIONAL_AUTOMATION_ENV = [
        "GITHUB_TOKEN",
        "VERCEL_TOKEN",
        "VERCEL_ORG_ID",
        "VERCEL_PROJECT_ID",
        "RAILWAY_TOKEN",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_PROJECT_ID",
    ]

    def check(self) -> None:
        present = []
        missing = []
        for key in self.LIVE_QA_ENV + self.OPTIONAL_AUTOMATION_ENV:
            if os.environ.get(key):
                present.append(key)
            else:
                missing.append(key)

        for key in self.LIVE_QA_ENV:
            if key not in present:
                self.add(
                    "warning",
                    f"Live QA URL not set: {key}",
                    recommendation="Set SITE_URL and API_URL as GitHub Actions secrets for live site/API checks."
                )

        optional_missing = [key for key in self.OPTIONAL_AUTOMATION_ENV if key not in present]
        if optional_missing:
            self.metrics["optional_automation_missing"] = optional_missing
            # These are not release blockers for normal QA. They are only needed for direct Vercel/Railway/GitHub mutation workflows.

        if not (self.root / ".github" / "workflows" / "devbareun-agentops.yml").exists():
            self.add("warning", "Root AgentOps workflow missing.", self.root / ".github" / "workflows")
        if not (self.backend_root / "Procfile").exists():
            self.add("warning", "Backend Procfile missing for Railway-style start command.", self.backend_root / "Procfile")

        self.metrics["secrets_present"] = present
        self.metrics["secrets_missing"] = missing
