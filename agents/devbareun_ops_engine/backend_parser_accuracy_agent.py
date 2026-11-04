from __future__ import annotations

from .agent_base import BaseAgent


class BackendParserAccuracyAgent(BaseAgent):
    name = "BackendParserAccuracyAgent"
    description = "Checks that the execution and delay analysis engine, its readers and its template are in place."

    # Engine modules under backend/app/delay/ and the input formats the reader must name.
    ENGINE_FILES = ["reader.py", "engine.py", "report.py", "sample.py", "model.py"]
    READER_TERMS = [".xer", ".xml", ".csv", ".xlsx", "planned_start", "actual_start", "responsible", "predecessors"]

    def check(self) -> None:
        delay_dir = self.backend_root / "app" / "delay"
        if not delay_dir.exists():
            self.add("critical", "Delay analysis engine folder not found.", delay_dir)
            return

        for file_name in self.ENGINE_FILES:
            path = delay_dir / file_name
            self.metrics[f"has_{file_name}"] = path.exists()
            if not path.exists():
                self.add("critical", f"Delay analysis module missing: {file_name}", path)

        reader = delay_dir / "reader.py"
        if reader.exists():
            text = self.read(reader).lower()
            for term in self.READER_TERMS:
                if term not in text:
                    self.add("warning", f"Delay reader may not handle: {term}", reader)

        template = self.frontend_root / "templates" / "devbareun-delay-analysis-template.xlsx"
        self.metrics["has_delay_template"] = template.exists()
        if not template.exists():
            self.add("warning", "Delay analysis Excel template not found.", template)

        if not any(f.severity.lower() in {"critical", "error", "fail"} for f in self.findings):
            self.add("info", "Delay analysis engine check completed without blocking issues.", delay_dir)
