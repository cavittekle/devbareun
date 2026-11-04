"""Construction execution and delay analysis (icra və gecikmə analizi)."""
from .engine import SCHEMA, analyze
from .reader import read_path, read_paths

__all__ = ["SCHEMA", "analyze", "read_path", "read_paths", "run_delay_analysis"]


def run_delay_analysis(paths, *, project=None, today=None, document_types=None):
    """Read uploaded files and return the delay analysis result dictionary.

    ``document_types`` maps a path (or file name) to ``contract``,
    ``schedule`` or ``f2``; files without a type are classified by name.
    """
    from .documents import read_documents

    data = read_documents(paths, document_types)
    if project:
        info = data.project
        if project.get("project_name") and info.name == "Construction project":
            info.name = project["project_name"]
        if project.get("currency") and not info.currency:
            info.currency = project["currency"]
    return analyze(data, today=today)
