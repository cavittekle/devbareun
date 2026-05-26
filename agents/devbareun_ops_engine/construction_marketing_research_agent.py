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
            "progress payment dashboard",
            "construction payment certificate analysis",
            "smeta actual cost comparison",
        ],
        "Full Project Control": [
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
        "Progress Payment": [
            "progress payment certificate software",
            "interim payment certificate construction",
            "hakediş software",
            "construction progress payment analysis",
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
        "Material Continuity": [
            "construction material continuity dashboard",
            "material shortage risk construction",
            "procurement delivery risk dashboard",
            "construction supply chain continuity",
        ],
        "Risk & Decisions": [
            "construction risk decision dashboard",
            "project risk register management actions",
            "construction executive decision support",
            "project controls risk dashboard",
        ],
    }

    def check(self) -> None:
        report = {
            "positioning": "DevBareun should be positioned as a construction project-control and reporting platform for owners, PMOs, construction managers and technical supervision teams.",
            "keyword_clusters": self.KEYWORD_CLUSTERS,
            "analysis_packages": {
                "Schedule Recovery": "Combines schedule delay and workforce signals into recovery actions.",
                "Cost & Payment Control": "Combines smeta/cost estimate and progress payment evidence into commercial control.",
                "Material Continuity": "Combines stock, procurement and delivery signals into continuity actions.",
                "Risk & Decisions": "Turns project risk evidence into decision prompts and recommended actions.",
                "Full Project Control": "Premium combined dashboard for schedule, workforce, cost, payment, material continuity, risk and decisions.",
            },
            "landing_page_sections": [
                "Choose Full Project Control, Schedule Recovery, Cost & Payment Control, Material Continuity or Risk & Decisions",
                "Upload smeta, BOQ, progress payment, schedule, workforce, material and risk files",
                "Confirm detected data before dashboard generation",
                "Data readiness, missing data and confidence score",
                "How-calculated formulas and source audit trail",
                "What-if scenarios and management action tracker",
                "Baseline vs actual project-control dashboard",
                "PDF and Excel management report export",
                "Designed for owners, PMOs and technical supervision teams",
            ],
            "blog_topics": [
                "How to compare planned progress and actual progress in construction",
                "How progress payment data can reveal project risk",
                "BOQ vs actual cost: early warning signals for cost overrun",
                "Construction manpower productivity: required crew vs actual crew",
                "Delay recovery planning from baseline and actual progress data",
                "Why audit trail and confidence scoring matter in construction project controls",
                "Using what-if scenarios for construction recovery and cost control",
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
