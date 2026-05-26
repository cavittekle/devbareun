from __future__ import annotations

import os
import sys
from .agent_base import BaseAgent


class BrowserQaAgent(BaseAgent):
    name = "BrowserQaAgent"
    description = "Optional Playwright smoke test for desktop/mobile visual regressions."

    def check(self) -> None:
        try:
            import playwright  # type: ignore
        except Exception:
            self.add("info", "Playwright is not installed; browser screenshot QA skipped.", recommendation="Install with: pip install playwright && python -m playwright install chromium")
            self.metrics["browser_qa"] = "skipped_no_playwright"
            return

        from playwright.sync_api import sync_playwright  # type: ignore

        site = os.environ.get("SITE_URL") or self.config.get("site_url")
        if not site:
            self.add("info", "SITE_URL not set; browser QA skipped.", recommendation="Set SITE_URL=https://devbareun.com or a Vercel preview URL.")
            return

        screenshots = self.out_dir / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for label, viewport in {"desktop": {"width": 1440, "height": 1000}, "iphone": {"width": 390, "height": 844}}.items():
                page = browser.new_page(viewport=viewport)
                page.goto(site, wait_until="networkidle", timeout=45000)
                page.screenshot(path=str(screenshots / f"{label}-home.png"), full_page=True)
                text = page.locator("body").inner_text(timeout=10000)
                if "Select analysis type" not in text and "Analiz növünü seçin" not in text:
                    self.add("warning", f"Upload selection label not found in {label} body text.", recommendation=str(screenshots / f"{label}-home.png"))
                page.close()
            browser.close()
        self.metrics["browser_screenshots_dir"] = str(screenshots)
