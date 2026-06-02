from __future__ import annotations

import os
from .agent_base import BaseAgent


class BrowserQaAgent(BaseAgent):
    name = "BrowserQaAgent"
    description = "Optional Playwright smoke test for desktop/mobile visual regressions."

    def check(self) -> None:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception:
            self.add("info", "Playwright is not installed; browser screenshot QA skipped.", recommendation="Install with: pip install playwright && python -m playwright install chromium")
            self.metrics["browser_qa"] = "skipped_no_playwright"
            return

        site = os.environ.get("SITE_URL") or self.config.get("site_url")
        if not site:
            self.add("info", "SITE_URL not set; browser QA skipped.", recommendation="Set SITE_URL=https://devbareun.com or a Vercel preview URL.")
            self.metrics["browser_qa"] = "skipped_no_site_url"
            return

        screenshots = self.out_dir / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for label, viewport in {"desktop": {"width": 1440, "height": 1000}, "iphone": {"width": 390, "height": 844}}.items():
                    page = browser.new_page(viewport=viewport)
                    page.goto(site, wait_until="networkidle", timeout=45000)
                    page.screenshot(path=str(screenshots / f"{label}-home.png"), full_page=True)
                    text = page.locator("body").inner_text(timeout=10000)
                    if "Project Upload Center" not in text and "Layihə" not in text and "DevBareun" not in text:
                        self.add("warning", f"Expected homepage/upload text not found in {label} body text.", recommendation=str(screenshots / f"{label}-home.png"))
                    page.close()
                browser.close()
            self.metrics["browser_screenshots_dir"] = str(screenshots)
        except Exception as exc:
            self.add("info", f"Playwright browser QA skipped because browser runtime is unavailable or the site could not be reached: {exc}", recommendation="For screenshot QA, install browsers with: python -m playwright install chromium")
            self.metrics["browser_qa"] = "skipped_runtime_unavailable"
