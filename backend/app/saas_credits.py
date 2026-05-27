from __future__ import annotations

from typing import Any, Dict, Optional

from .saas_store import list_rows, update_one, insert
from .saas_ids import make_public_id

PLAN_CREDIT_LIMITS = {"single": 1, "plus": 5, "pro": 20}


def credit_summary(owner_email: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    rows = [r for r in list_rows("analysis_credits", owner_email=owner_email) if r.get("status") == "active"] if owner_email else []
    if project_id:
        project_rows = [r for r in list_rows("analysis_credits", project_id=project_id) if r.get("status") == "active"]
        rows.extend(project_rows)
    # de-duplicate by credit_id
    seen = set()
    unique = []
    for row in rows:
        cid = row.get("credit_id")
        if cid not in seen:
            unique.append(row)
            seen.add(cid)
    total = sum(int(r.get("total_credits") or 0) for r in unique)
    used = sum(int(r.get("used_credits") or 0) for r in unique)
    remaining = sum(int(r.get("remaining_credits") or 0) for r in unique)
    return {"total": total, "used": used, "remaining": remaining, "credits": unique}


def require_credit(owner_email: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    summary = credit_summary(owner_email=owner_email, project_id=project_id)
    if summary["remaining"] <= 0:
        return {"allowed": False, "reason": "No analysis credits available.", **summary}
    return {"allowed": True, **summary}


def consume_credit(owner_email: Optional[str], project_id: Optional[str], analysis_id: str) -> Dict[str, Any]:
    check = require_credit(owner_email=owner_email, project_id=project_id)
    if not check["allowed"]:
        return check
    for row in check["credits"]:
        remaining = int(row.get("remaining_credits") or 0)
        if remaining > 0:
            used = int(row.get("used_credits") or 0) + 1
            updated = update_one("analysis_credits", "credit_id", row["credit_id"], {
                "used_credits": used,
                "remaining_credits": remaining - 1,
            })
            insert("subscription_usage", {
                "usage_id": make_public_id("credit").replace("DB-CRD", "DB-USG"),
                "credit_id": row["credit_id"],
                "analysis_id": analysis_id,
                "owner_email": owner_email,
                "project_id": project_id,
                "used": 1,
            })
            return {"allowed": True, "consumed": True, "credit": updated}
    return {"allowed": False, "reason": "Credit record could not be consumed."}
