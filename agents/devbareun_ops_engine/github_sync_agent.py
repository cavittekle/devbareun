from __future__ import annotations

import os

from .agent_base import BaseAgent


class GitHubSyncAgent(BaseAgent):
    """Audit GitHub auto-upload configuration without mutating repositories."""

    name = "GitHubSyncAgent"
    description = "Checks whether the GitHub auto-upload tool and repository sync options are ready."

    def check(self) -> None:
        upload_script = self.root / "tools" / "github_auto_upload.py"
        if not upload_script.exists():
            self.add("critical", "GitHub auto-upload tool is missing.", upload_script)
            return

        text = self.read(upload_script)
        self.metrics["upload_tool"] = str(upload_script.relative_to(self.root))
        self.metrics["frontend_exists"] = self.frontend_root.exists()
        self.metrics["backend_exists"] = self.backend_root.exists()
        self.metrics["token_present"] = bool(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))
        self.metrics["clean_sync_supported"] = "--clean" in text

        if not self.frontend_root.exists():
            self.add("critical", "frontend/ folder was not found; frontend sync would fail.", self.frontend_root)
        if not self.backend_root.exists():
            self.add("critical", "backend/ folder was not found; backend sync would fail.", self.backend_root)

        if not self.metrics["token_present"]:
            self.add("info", "GITHUB_TOKEN/GH_TOKEN is not set. Auto-upload dry-run works; live sync needs GH_SYNC_TOKEN or a GitHub token.", recommendation="Add GH_SYNC_TOKEN only if you want the auto-upload workflow to push/PR changes.")

        if "--clean" not in text:
            self.add("warning", "Auto-upload tool does not expose --clean mode, so old files may remain in target repos.", upload_script)
        else:
            self.metrics["clean_sync_supported"] = True

        if "agentops-auto-sync" not in text:
            self.add("warning", "Safe PR branch name is not visible in the auto-upload tool.", upload_script)

        if not self.findings:
            self.add("info", "GitHub auto-upload is installed with safe PR branch defaults and clean-sync support.", upload_script)
