from __future__ import annotations

import re
from .agent_base import BaseAgent


class LanguageAuditAgent(BaseAgent):
    name = "LanguageAuditAgent"
    description = "Finds Turkish/English hardcoded dynamic text issues and public copy terminology conflicts."

    TURKISH_TERMS = [
        "Maliyet", "Gerçekte", "tamamlanan", "yürütme", "İsteğe", "Başlangıç", "bitiş", "Tahmini", "manuelo",
        "seçiniz", "tutar", "miktar", "fiyat"
    ]
    PUBLIC_FORBIDDEN = [
        " artificial intelligence ", " süni intellekt ", " ai powered", " ai-powered", " ai "
    ]

    def check(self) -> None:
        files = list(self.iter_files(self.frontend_root, ["*.html", "*.js"]))
        for path in files:
            text = self.read(path)
            low = " " + text.lower() + " "
            for term in self.TURKISH_TERMS:
                if term.lower() in low:
                    self.add("warning", f"Possible Turkish hardcoded text remains: {term}", path, recommendation="Move this text into EN/AZ dictionary or glossary.")
            if path.suffix == ".html" or "i18n" in path.name or "app" in path.name:
                for term in self.PUBLIC_FORBIDDEN:
                    if term in low:
                        self.add("warning", f"Public copy contains forbidden wording: {term.strip()}", path, recommendation="Use construction analytics / project control wording instead of AI language.")
        i18n = self.frontend_root / "js" / "i18n-extended.js"
        if i18n.exists():
            text = self.read(i18n)
            must = ["stepSelectAnalysis", "downloadOptionalTemplate", "template_all_text", "analysisCostTitle", "analysisScheduleTitle", "analysisAllTitle", "packageCostKicker", "packageScheduleKicker"]
            for key in must:
                if key not in text:
                    self.add("warning", f"Missing translation key: {key}", i18n)
        else:
            self.add("warning", "js/i18n-extended.js not found.", i18n)
        self.metrics["frontend_text_files_checked"] = len(files)
