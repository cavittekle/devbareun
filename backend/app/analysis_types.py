from __future__ import annotations

PREMIUM_ANALYSIS_TYPE = "full_project_control_premium"


def normalize_analysis_type(value: str | None) -> str:
    key = (value or "all").strip().lower().replace("-", "_")
    aliases = {
        "": PREMIUM_ANALYSIS_TYPE,
        "all": PREMIUM_ANALYSIS_TYPE,
        "full": PREMIUM_ANALYSIS_TYPE,
        "full_project_control": PREMIUM_ANALYSIS_TYPE,
        "full_project_control_premium": PREMIUM_ANALYSIS_TYPE,
        "premium": PREMIUM_ANALYSIS_TYPE,
        "executive": PREMIUM_ANALYSIS_TYPE,
        "dashboard": PREMIUM_ANALYSIS_TYPE,
        "cost_analysis": "cost",
        "schedule_delay": "schedule",
        "planning": "schedule",
        "material_continuity": "material",
        "procurement": "material",
        "materials": "material",
        "decision": "risk",
        "decisions": "risk",
        "risk_decisions": "risk",
        "manpower": "workforce",
        "labor": "workforce",
        "f2": "progress",
        "f_2": "progress",
        "forma2": "progress",
    }
    key = aliases.get(key, key)
    return key if key in {PREMIUM_ANALYSIS_TYPE, "cost", "schedule", "workforce", "progress", "material", "risk"} else PREMIUM_ANALYSIS_TYPE


def parser_analysis_type(value: str | None) -> str:
    key = normalize_analysis_type(value)
    return "all" if key == PREMIUM_ANALYSIS_TYPE else key
