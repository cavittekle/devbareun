from __future__ import annotations

from .analysis_types import PREMIUM_ANALYSIS_TYPE

COMBINED_REQUIRED_SHEETS = [
    "Project_Info",
    "Baseline_Schedule",
    "Actual_Progress",
    "Cost_Estimate",
    "F2_Progress_Payment",
    "Workforce",
    "Material_Stock",
    "Risk_Register",
]

LEGACY_DASHBOARD_SHEETS = [
    "README",
    "Full_Dashboard_Input",
    "Cost_Estimate_Smeta",
    "F2_Progress_Payment",
    "Schedule_Plan_Actual",
    "Workforce_Productivity",
    "Equipment_Usage",
    "Lists",
]

TEMPLATE_MANIFEST = {
    PREMIUM_ANALYSIS_TYPE: {
        "title": "Project Control Combined Template",
        "file": "devbareun-full-project-control-template.xlsx",
        "required_sheets": COMBINED_REQUIRED_SHEETS,
        "purpose": "Complete project-control template for schedule, cost/payment, workforce, material, risk and recovery actions.",
    },
    "all": {
        "title": "Project Control Combined Template",
        "file": "devbareun-full-project-control-template.xlsx",
        "required_sheets": COMBINED_REQUIRED_SHEETS,
        "purpose": "Backward-compatible alias for the combined project-control template.",
    },
    "schedule": {
        "title": "Schedule Recovery Template",
        "file": "devbareun-schedule-recovery-template.xlsx",
        "required_sheets": ["Baseline_Schedule", "Actual_Progress", "Workforce", "Recovery_Target"],
        "purpose": "Delay, workforce gap and recovery planning template.",
    },
    "cost": {
        "title": "Cost & Payment Control Template",
        "file": "devbareun-cost-payment-control-template.xlsx",
        "required_sheets": ["Cost_Estimate", "F2_Progress_Payment", "Actual_Cost", "Variation_Orders"],
        "purpose": "Cost estimate, F-2 / Progress Payment and commercial control template.",
    },
    "progress": {
        "title": "Progress / F-2 Template",
        "file": "devbareun-progress-template.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "Progress, F-2 payment and dashboard input template for legacy/import workflows.",
    },
    "workforce": {
        "title": "Workforce Productivity Template",
        "file": "devbareun-workforce-template.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "Workforce productivity, equipment usage and dashboard input template.",
    },
    "material": {
        "title": "Material Continuity Template",
        "file": "devbareun-material-continuity-template.xlsx",
        "required_sheets": ["Material_Stock", "Delivery_Schedule", "Consumption_Rate", "Critical_Materials"],
        "purpose": "Stock, delivery, consumption and procurement continuity template.",
    },
    "risk": {
        "title": "Risk & Decisions Template",
        "file": "devbareun-risk-decisions-template.xlsx",
        "required_sheets": ["Risk_Register", "Decision_Log", "Open_Issues", "Management_Actions"],
        "purpose": "Risk register, decision log and management action template.",
    },
    "professional_upload": {
        "title": "Professional Upload Template v2",
        "file": "devbareun-professional-upload-template-v2.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "General upload template linked from the public landing page.",
    },
    "executive_dashboard": {
        "title": "Executive Dashboard Template",
        "file": "devbareun-executive-dashboard-template.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "Executive dashboard input template for legacy/import workflows.",
    },
    "legacy_cost": {
        "title": "Legacy Cost Template",
        "file": "devbareun-cost-template.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "Legacy cost dashboard template retained for backward-compatible downloads.",
    },
    "legacy_schedule": {
        "title": "Legacy Schedule Template",
        "file": "devbareun-schedule-template.xlsx",
        "required_sheets": LEGACY_DASHBOARD_SHEETS,
        "purpose": "Legacy schedule dashboard template retained for backward-compatible downloads.",
    },
}
