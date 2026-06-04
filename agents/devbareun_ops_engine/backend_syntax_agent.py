from __future__ import annotations

import py_compile
from .agent_base import BaseAgent


class BackendSyntaxAgent(BaseAgent):
    name = "BackendSyntaxAgent"
    description = "Compiles backend Python files and reports syntax failures."

    def check(self) -> None:
        if not self.backend_root.exists():
            self.add("critical", "Backend folder not found.", self.backend_root)
            return
        files = list(self.iter_files(self.backend_root, ["*.py"]))
        for path in files:
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                self.add("critical", f"Python compile failed: {exc}", path)
        self.metrics["python_files_checked"] = len(files)
