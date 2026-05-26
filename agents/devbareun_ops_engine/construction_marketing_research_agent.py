from __future__ import annotations

import json
from .agent_base import BaseAgent


class ConstructionMarketingResearchAgent(BaseAgent):
    name = "ConstructionMarketingResearchAgent"
    description = "Creates construction SaaS keyword clusters, positioning ideas and content tasks."

    KEYWORD_CLUSTERS = {
        "Project control dashboard": [
            "construction project control dashboard",
            "construction management dashboard",
            "project progress dashboard",
            "baseline vs actual construction dashboard",
        ],
        "Cost / BOQ / Smeta analytics": [
            "construction cost estimate analysis",
            "BOQ analysis software",
            "construction cost overrun dashboard",
            "smeta analysis platform",
        ],
        "Progress payment / F-2": [
            "progress payment certificate software",
            "interim payment certificate construction",
            "hakediş software",
            "F-2 construction payment analysis",
        ],
        "Schedule delay": [
            "construction delay analysis dashboard",
            "Primavera schedule delay analysis",
            "planned vs actual schedule construction",
            "recovery plan construction delay",
        ],
        "Workforce productivity": [
            "construction manpower productivity tracking",
            "workforce planning construction",
            "crew productivity dashboard",
            "construction labor productivity analysis",
        ],
    }

    def check(self) -> None:
        report = {
            "positioning": "DevBareun should be positioned as a construction project-control and reporting platform for owners, PMOs, construction managers and technical supervision teams.",
            "keyword_clusters": self.KEYWORD_CLUSTERS,
            "landing_page_sections": [
                "Upload smeta, BOQ, F-2, schedule and workforce files",
                "Confirm detected data before dashboard generation",
                "Baseline vs actual project-control dashboard",
                "PDF and Excel management report export",
                "Designed for owners, PMOs and technical supervision teams",
            ],
            "blog_topics": [
                "How to compare planned progress and actual progress in construction",
                "How F-2 / interim payment data can reveal project risk",
                "BOQ vs actual cost: early warning signals for cost overrun",
                "Construction manpower productivity: required crew vs actual crew",
                "Delay recovery planning from baseline and actual progress data",
            ],
            "markets": {
                "Azerbaijan": "Use Smeta, F-2, layihə nəzarəti, texniki nəzarət, sifarişçi dashboardu wording.",
                "Turkey": "Use Hakediş, metraj, yaklaşık maliyet, şantiye ilerleme dashboardu wording.",
                "GCC": "Use project controls, progress payment certificate, baseline schedule, cost overrun, PMO reporting wording.",
            },
        }
        path = self.out_dir / "construction_marketing_research.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.metrics.update(report)
