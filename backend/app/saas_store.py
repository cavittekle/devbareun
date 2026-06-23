
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from .saas_ids import make_public_id, make_guest_token, expiry

BASE_DIR = Path(__file__).resolve().parent.parent
SAAS_DATA_DIR = BASE_DIR / "data" / "saas"
SAAS_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = SAAS_DATA_DIR / "saas_pilot_store.json"

TABLES = [
    "users", "companies", "projects", "uploaded_files", "analysis_jobs", "analysis_results", "reports",
    "plans", "subscriptions", "payments", "guest_orders", "checkout_sessions",
    "analysis_credits", "subscription_usage", "credit_transactions", "support_tickets",
    "admin_notes", "activity_logs", "audit_logs", "data_lifecycle_requests", "project_activity_events"
]


def _empty() -> Dict[str, List[Dict[str, Any]]]:
    return {name: [] for name in TABLES}


def load_store() -> Dict[str, List[Dict[str, Any]]]:
    if not DB_FILE.exists():
        return _empty()
    try:
        data = json.loads(DB_FILE.read_text(encoding="utf-8"))
        for table in TABLES:
            data.setdefault(table, [])
        return data
    except Exception:
        return _empty()


def save_store(data: Dict[str, List[Dict[str, Any]]]) -> None:
    DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def now() -> str:
    return datetime.utcnow().isoformat()


def insert(table: str, record: Dict[str, Any]) -> Dict[str, Any]:
    data = load_store()
    row = dict(record)
    row.setdefault("id", uuid4().hex)
    row.setdefault("created_at", now())
    row.setdefault("updated_at", now())
    data.setdefault(table, []).append(row)
    save_store(data)
    return row


def list_rows(table: str, **filters: Any) -> List[Dict[str, Any]]:
    rows = load_store().get(table, [])
    for key, value in filters.items():
        if value is not None:
            rows = [row for row in rows if row.get(key) == value]
    return rows


def find_one(table: str, **filters: Any) -> Dict[str, Any] | None:
    rows = list_rows(table, **filters)
    return rows[0] if rows else None


def update_one(table: str, public_key: str, public_value: str, patch: Dict[str, Any]) -> Dict[str, Any] | None:
    data = load_store()
    rows = data.get(table, [])
    for row in rows:
        if row.get(public_key) == public_value:
            row.update(patch)
            row["updated_at"] = now()
            save_store(data)
            return row
    return None


def create_guest_order(email: str, project_name: str | None, result_days: int = 14) -> Dict[str, Any]:
    guest_order = insert("guest_orders", {
        "guest_order_id": make_public_id("guest_order"),
        "email": email,
        "status": "draft",
        "result_token": make_guest_token(),
        "result_expires_at": expiry(result_days),
    })
    project = insert("projects", {
        "project_id": make_public_id("project"),
        "guest_order_id": guest_order["guest_order_id"],
        "project_name": project_name or "Guest construction project",
        "status": "draft",
        "currency": "AZN",
    })
    insert("analysis_credits", {
        "credit_id": make_public_id("credit"),
        "source": "single_project",
        "owner_email": email,
        "total_credits": 1,
        "used_credits": 0,
        "remaining_credits": 1,
        "status": "pending_payment",
    })
    return {"guest_order": guest_order, "project": project}


def log_activity(actor: str | None, event: str, payload: Dict[str, Any] | None = None) -> None:
    insert("activity_logs", {
        "actor": actor or "system",
        "event": event,
        "payload": payload or {},
    })
