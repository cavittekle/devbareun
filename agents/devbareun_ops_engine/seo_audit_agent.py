from __future__ import annotations

import re
from .agent_base import BaseAgent


class SeoAuditAgent(BaseAgent):
    name = "SeoAuditAgent"
    description = "Checks SEO basics: title, description, canonical, OG tags, robots and sitemap."

    HTML_FILES = ["index.html", "about.html", "faq.html", "contact.html", "privacy.html", "terms.html"]

    def check(self) -> None:
        for name in self.HTML_FILES:
            path = self.frontend_root / name
            if not path.exists():
                self.add("warning", f"SEO page missing: {name}", path)
                continue
            html = self.read(path)
            if "<title>" not in html:
                self.add("warning", "Missing <title>.", path)
            desc_tag = re.search(r'<meta[^>]*>', html, re.I)
            desc = None
            for tag in re.findall(r'<meta[^>]*>', html, re.I):
                if re.search(r'name=["\']description["\']', tag, re.I):
                    desc = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
                    break
            if not desc:
                self.add("warning", "Missing meta description.", path)
            elif len(desc.group(1)) < 70:
                self.add("warning", "Meta description is short.", path)
            for marker in ["og:title", "og:description", "theme-color"]:
                if marker not in html:
                    self.add("warning", f"Missing meta marker: {marker}", path)
        robots = self.frontend_root / "robots.txt"
        sitemap = self.frontend_root / "sitemap.xml"
        if not robots.exists():
            self.add("warning", "robots.txt missing.", robots)
        else:
            r = self.read(robots)
            if "Sitemap:" not in r:
                self.add("warning", "robots.txt missing Sitemap directive.", robots)
            if "Allow: / Sitemap:" in r:
                self.add("warning", "robots.txt has Allow and Sitemap on same line; split them.", robots, recommendation="Use two lines: Allow: / and Sitemap: https://devbareun.com/sitemap.xml")
        if not sitemap.exists():
            self.add("warning", "sitemap.xml missing.", sitemap)
        self.metrics["seo_pages_checked"] = len(self.HTML_FILES)
