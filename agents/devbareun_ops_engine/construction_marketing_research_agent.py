from __future__ import annotations

import json
from .agent_base import BaseAgent


class ConstructionMarketingResearchAgent(BaseAgent):
    name = "ConstructionMarketingResearchAgent"
    description = "Creates construction SaaS keyword clusters, positioning ideas and content tasks."

    KEYWORD_CLUSTERS = {
        "Schedule Recovery": [
            "construction schedule recovery dashboard",
            "construction delay recovery plan",
            "baseline vs actual schedule and manpower",
            "project recovery planning construction",
        ],
        "Cost & Payment Control": [
            "construction cost and payment control",
            "F-2 progress payment dashboard",
            "construction payment certificate analysis",
            "smeta actual cost comparison",
        ],
        "Full Dashboard": [
            "construction project control dashboard",
            "executive construction dashboard",
            "construction risk and cost dashboard",
            "PMO project control reporting",
        ],
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
            "analysis_packages": {
                "Schedule Recovery": "Combines schedule delay and workforce signals into recovery actions.",
                "Cost & Payment Control": "Combines smeta/cost estimate and F-2/progress payment evidence into commercial control.",
                "Full Dashboard": "Premium combined dashboard for schedule, workforce, cost, F-2, risk and reports.",
            },
            "landing_page_sections": [
                "Choose Schedule Recovery, Cost & Payment Control or Full Dashboard",
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
