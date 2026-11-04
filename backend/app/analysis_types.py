from __future__ import annotations

# DevBareun has one analysis: construction execution and delay analysis.
DELAY_ANALYSIS_TYPE = "delay"


def normalize_analysis_type(value: str | None) -> str:
    """Return the canonical analysis type.

    Saved jobs and older clients may still send retired types such as
    ``schedule``, ``cost`` or ``full_project_control_premium``; every request
    now runs the delay analysis.
    """
    return DELAY_ANALYSIS_TYPE
