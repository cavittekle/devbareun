from __future__ import annotations

import re
from pathlib import Path
from .agent_base import BaseAgent


class FrontendReadabilityAgent(BaseAgent):
    name = "FrontendReadabilityAgent"
    description = "Checks dark/light readability, upload step labels, contrast-sensitive CSS and mobile layout safeguards."

    REQUIRED_CSS_SNIPPETS = [
        "#upload .flow-step-label",
        "#upload .flow-step-label > span:last-child",
        "text-shadow",
        "html[data-theme=\"light\"] #upload",
        "analysis-type-card",
    ]

    def check(self) -> None:
        css = self.frontend_root / "css" / "styles.css"
        if not css.exists():
            self.add("critical", "frontend/css/styles.css not found.", css)
            return
        text = self.read(css)
        for snippet in self.REQUIRED_CSS_SNIPPETS:
            if snippet not in text:
                self.add("warning", f"Readability guard missing: {snippet}", css, recommendation="Keep upload wizard, package-card and card contrast overrides in styles.css.")

        weak_muted = re.search(r"--muted\s*:\s*#(?:6[0-9a-f]{4}|7[0-9a-f]{4}|8[0-9a-f]{4})", text, re.I)
        if weak_muted:
            self.add("warning", "Muted color may be too dark for the approved dark interface.", css, recommendation="Use lighter muted text for dark background, especially upload flow helper text.")

        if "overflow:hidden" in text and "#upload .analysis-type-card" in text and "z-index" not in text[text.find("#upload .analysis-type-card"):text.find("#upload .analysis-type-card")+800]:
            self.add("warning", "Analysis card uses overflow hidden without a nearby z-index/readability override.", css)

        html = self.frontend_root / "index.html"
        if html.exists():
            h = self.read(html)
            required = ["upload-packages-v118", "package-card-row", "packageComboTitle", "analysis-type-grid", "analysisRequirements"]
            for item in required:
                if item not in h:
                    self.add("warning", f"Upload flow marker missing: {item}", html)
        else:
            self.add("critical", "index.html not found.", html)

        self.metrics["css_size_bytes"] = css.stat().st_size
