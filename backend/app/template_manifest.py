from __future__ import annotations

from .analysis_types import DELAY_ANALYSIS_TYPE

DELAY_ANALYSIS_TEMPLATE_FILE = "devbareun-delay-analysis-template.xlsx"

DELAY_ANALYSIS_SHEETS = [
    "README",
    "Layihe_Project",
    "Plan_Qrafik_Baseline",
    "Faktiki_Icra_Actual",
    "Gecikme_Hadiseleri_Events",
    "Ayliq_Icra_Monthly",
]

TEMPLATE_MANIFEST = {
    DELAY_ANALYSIS_TYPE: {
        "title": "Execution and Delay Analysis Template",
        "file": DELAY_ANALYSIS_TEMPLATE_FILE,
        "required_sheets": DELAY_ANALYSIS_SHEETS,
        "purpose": "Baseline schedule, actual progress, delay events and monthly progress for the execution and delay analysis report.",
    },
}
