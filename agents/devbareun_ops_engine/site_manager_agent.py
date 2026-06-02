from __future__ import annotations

import os
import urllib.error
from .agent_base import BaseAgent


class SiteManagerAgent(BaseAgent):
    name = "SiteManagerAgent"
    description = "Checks live site uptime, backend health, key routes, broken links and customer journey endpoints."

    def check(self) -> None:
        site = os.environ.get("SITE_URL") or self.config.get("site_url")
        api = os.environ.get("API_URL") or self.config.get("api_url")
        if not site and not api:
            self.add("info", "Live site checks skipped because SITE_URL/API_URL are not configured.", recommendation="Set SITE_URL and API_URL in GitHub Actions secrets to enable uptime checks.")
            self.metrics["site_manager"] = "skipped_no_urls"
            return
        site = site or "https://devbareun.com"
        api = api or "https://devbareun-backend-production.up.railway.app"
        paths = ["/", "/about.html", "/faq.html", "/contact.html", "/privacy.html", "/terms.html", "/result-dashboard.html"]
        checked = 0
        for p in paths:
            url = site.rstrip("/") + p
            try:
                status, body = self.http_get(url, timeout=15)
                checked += 1
                if status >= 400:
                    self.add("critical", f"Route returned HTTP {status}: {url}")
                if p == "/" and "DevBareun" not in body:
                    self.add("warning", "Homepage response does not include DevBareun brand text.", recommendation=url)
            except Exception as exc:
                self.add("warning", f"Could not check route {url}: {exc}")
        for h in ["/health", "/api/health"]:
            url = api.rstrip("/") + h
            try:
                status, body = self.http_get(url, timeout=15)
                if status >= 400:
                    self.add("critical", f"Backend health returned HTTP {status}: {url}")
                if "ok" not in body.lower() and "version" not in body.lower():
                    self.add("warning", f"Backend health response looks unexpected: {url}", recommendation=body[:300])
            except Exception as exc:
                self.add("warning", f"Could not check backend health {url}: {exc}")
        self.metrics["site_url"] = site
        self.metrics["api_url"] = api
        self.metrics["routes_checked"] = checked
