from __future__ import annotations

from .analysis_types import DELAY_ANALYSIS_TYPE

DELAY_ANALYSIS_TEMPLATE_FILE = "devbareun-delay-analysis-template.xlsx"

DELAY_ANALYSIS_SHEETS = [
    "README",
    "Layihe_Project",
    "Muqavile_Contract",
    "Plan_Qrafik_Baseline",
    "Faktiki_Icra_Actual",
    "Smeta_F2_Nakopitel",
    "F3_Forma3",
    "F2_Odenisler_Payments",
    "Gecikme_Hadiseleri_Events",
    "Ayliq_Icra_Monthly",
]

TEMPLATE_MANIFEST = {
    DELAY_ANALYSIS_TYPE: {
        "title": "Execution and Delay Analysis Template",
        "file": DELAY_ANALYSIS_TEMPLATE_FILE,
        "required_sheets": DELAY_ANALYSIS_SHEETS,
        "purpose": "Contract terms, baseline schedule, actual progress, estimate with cumulative F-2, Forma-3, F-2 payments and delay events for the execution and delay analysis report.",
    },
}
