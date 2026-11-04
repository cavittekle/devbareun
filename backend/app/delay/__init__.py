"""Construction execution and delay analysis (icra və gecikmə analizi)."""
from .engine import SCHEMA, analyze
from .reader import read_path, read_paths

__all__ = ["SCHEMA", "analyze", "read_path", "read_paths", "run_delay_analysis"]


def run_delay_analysis(paths, *, project=None, today=None):
    """Read uploaded files and return the delay analysis result dictionary."""
    data = read_paths(paths)
    if project:
        info = data.project
        if project.get("project_name") and info.name == "Construction project":
            info.name = project["project_name"]
        if project.get("currency") and not info.currency:
            info.currency = project["currency"]
    return analyze(data, today=today)
