from __future__ import annotations

import re
from .agent_base import BaseAgent


class SecuritySecretsAgent(BaseAgent):
    name = "SecuritySecretsAgent"
    description = "Scans for likely secrets, unsafe production permissions and public sensitive patterns."

    SECRET_PATTERNS = [
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"railway_[A-Za-z0-9_\\-]{20,}",
        r"vercel_[A-Za-z0-9_\\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
    ]

    def check(self) -> None:
        files = list(self.iter_files(self.root, ["*.py", "*.js", "*.html", "*.yml", "*.yaml", "*.json", "*.env", "*.txt"]))
        for path in files:
            if path.name.endswith(".example"):
                continue
            text = self.read(path)
            for pattern in self.SECRET_PATTERNS:
                if re.search(pattern, text):
                    self.add("critical", f"Possible secret detected matching pattern {pattern}", path, recommendation="Move secrets to GitHub/Vercel/Railway environment variables.")
            if ".env" == path.name and "example" not in path.name.lower():
                self.add("warning", ".env file found in package.", path, recommendation="Never commit real .env files.")
        main = self.backend_root / "app" / "main.py"
        if main.exists():
            text = self.read(main)
            if 'allow_origins=["*"]' in text.replace(" ", ""):
                self.add("warning", "CORS currently allows all origins.", main, recommendation="For production, restrict CORS to devbareun.com and Vercel preview domains.")
        self.metrics["security_files_checked"] = len(files)
