from __future__ import annotations

from pathlib import Path
from .agent_base import BaseAgent


class BackendParserAccuracyAgent(BaseAgent):
    name = "BackendParserAccuracyAgent"
    description = "Checks DevBareun construction parser coverage using the active AgentOps parser checks."

    REQUIRED_TERMS = ["smeta", "boq", "f-2", "forma", "progress", "schedule", "workforce", "currency"]
    IMPORTANT_FILES = ["parser.py", "analyzer.py", "models.py", "reports.py", "openai_mapper.py"]

    def check(self) -> None:
        app_dir = self.backend_root / "app"
        if not app_dir.exists():
            self.add("critical", "Backend app folder not found.", app_dir)
            return

        combined_text_parts = []
        for file_name in self.IMPORTANT_FILES:
            path = app_dir / file_name
            if path.exists():
                text = self.read(path)
                combined_text_parts.append(text.lower())
                self.metrics[f"has_{file_name}"] = True
            else:
                self.metrics[f"has_{file_name}"] = False
                if file_name in {"parser.py", "analyzer.py", "models.py"}:
                    self.add("critical", f"Required backend parser file missing: {file_name}", path)
                else:
                    self.add("warning", f"Optional backend support file missing: {file_name}", path)

        combined = "\n".join(combined_text_parts)
        for term in self.REQUIRED_TERMS:
            if term not in combined:
                self.add("warning", f"Parser/analyzer may not explicitly handle construction term: {term}", app_dir)

        template = self.frontend_root / "templates" / "devbareun-professional-upload-template-v2.xlsx"
        self.metrics["has_professional_excel_template"] = template.exists()
        if not template.exists():
            self.add("warning", "Professional Excel upload template not found.", template)

        if not any(f.severity.lower() in {"critical", "error", "fail"} for f in self.findings):
            self.add("info", "Backend parser coverage check completed without blocking issues.", app_dir)
