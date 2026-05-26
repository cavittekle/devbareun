from __future__ import annotations

import os
from pathlib import Path
from .agent_base import BaseAgent


class DeploymentReadinessAgent(BaseAgent):
    name = "DeploymentReadinessAgent"
    description = "Verifies GitHub/Vercel/Railway CI/CD readiness without pushing production changes."

    SECRET_ENV = [
        "GITHUB_TOKEN",
        "VERCEL_TOKEN",
        "VERCEL_ORG_ID",
        "VERCEL_PROJECT_ID",
        "RAILWAY_TOKEN",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_PROJECT_ID",
        "SITE_URL",
        "API_URL",
    ]

    def check(self) -> None:
        present = []
        missing = []
        for key in self.SECRET_ENV:
            if os.environ.get(key):
                present.append(key)
            else:
                missing.append(key)
        # Tokens are optional locally, but required for full live automation.
        for key in missing:
            if key in {"SITE_URL", "API_URL"}:
                continue
            self.add("warning", f"Deployment secret not set: {key}", recommendation="Set this as a GitHub Actions secret or platform environment variable.")
        if not (self.root / ".github" / "workflows" / "devbareun-agentops.yml").exists():
            self.add("warning", "Root AgentOps workflow missing.", self.root / ".github" / "workflows")
        if not (self.backend_root / "Procfile").exists():
            self.add("warning", "Backend Procfile missing for Railway-style start command.", self.backend_root / "Procfile")
        self.metrics["secrets_present"] = present
        self.metrics["secrets_missing"] = missing
