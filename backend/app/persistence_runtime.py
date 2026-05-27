
"""
DevBareun Persistence Runtime
v1.3.7 — Persistent Analysis + Report Archive + A4/A3 Print Metadata

This module provides a lightweight persistence abstraction.
Production target: Supabase PostgreSQL.
Pilot fallback: in-memory store so the SaaS flow can be tested before DB keys are configured.
"""
from __future__ import annotations

import os
import time
import secrets
from typing import Any, Dict, List, Optional

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_PROJECTS: Dict[str, Dict[str, Any]] = {}
_ANALYSES: Dict[str, Dict[str, Any]] = {}
_REPORTS: Dict[str, Dict[str, Any]] = {}
_GUEST_RESULTS: Dict[str, Dict[str, Any]] = {}


def _id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


def new_project_id() -> str:
    return _id("DB-PRJ")


def new_analysis_id() -> str:
    return _id("DB-ANL")


def new_report_id() -> str:
    return _id("DB-RPT")


def new_guest_token() -> str:
    return "DB-GUEST-" + secrets.token_urlsafe(20).replace("-", "").replace("_", "")[:28].upper()


def now_ts() -> int:
    return int(time.time())


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and httpx is not None)


async def supabase_insert(table: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not supabase_configured():
        return None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase insert failed for {table}: {resp.text[:300]}")
    data = resp.json()
    return data[0] if isinstance(data, list) and data else data


async def supabase_select(table: str, query: str) -> Optional[List[Dict[str, Any]]]:
    if not supabase_configured():
        return None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/{table}?{query}", headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase select failed for {table}: {resp.text[:300]}")
    return resp.json()


async def save_project(owner_email: str, project: Dict[str, Any]) -> Dict[str, Any]:
    project_id = project.get("project_id") or new_project_id()
    record = {
        **project,
        "project_id": project_id,
        "owner_email": owner_email,
        "created_at_ts": now_ts(),
        "status": project.get("status", "active"),
    }
    if supabase_configured():
        saved = await supabase_insert("projects", record)
        return saved or record
    _PROJECTS[project_id] = record
    return record


async def list_projects(owner_email: str) -> List[Dict[str, Any]]:
    if supabase_configured():
        rows = await supabase_select(
            "projects",
            f"select=*&owner_email=eq.{owner_email}&order=created_at_ts.desc",
        )
        return rows or []
    return sorted(
        [p for p in _PROJECTS.values() if p.get("owner_email") == owner_email],
        key=lambda x: x.get("created_at_ts", 0),
        reverse=True,
    )


async def save_analysis(owner_email: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_id = payload.get("analysis_id") or new_analysis_id()
    project_id = payload.get("project_id")
    report_id = payload.get("report_id") or new_report_id()
    record = {
        **payload,
        "analysis_id": analysis_id,
        "report_id": report_id,
        "owner_email": owner_email,
        "created_at_ts": now_ts(),
        "status": payload.get("status", "completed"),
    }
    if supabase_configured():
        saved = await supabase_insert("analysis_results", record)
        record = saved or record
    else:
        _ANALYSES[analysis_id] = record

    # v1.3.7: every saved analysis receives an archive report row for
    # report history, A4/A3 print routing and future PDF/Excel storage links.
    try:
        await save_report_archive(owner_email, {
            **record,
            "source": "analysis_save",
            "report_type": "dashboard",
            "print_size": payload.get("print_size") or "A4",
            "language": payload.get("language") or "en",
        })
    except Exception:
        # Do not block dashboard saving if the optional archive table has not
        # been migrated yet. Deployment QA will surface the archive issue.
        pass
    return record


async def get_analysis(owner_email: str, analysis_id: str) -> Optional[Dict[str, Any]]:
    if supabase_configured():
        rows = await supabase_select(
            "analysis_results",
            f"select=*&analysis_id=eq.{analysis_id}&owner_email=eq.{owner_email}&limit=1",
        )
        return rows[0] if rows else None
    row = _ANALYSES.get(analysis_id)
    if row and row.get("owner_email") == owner_email:
        return row
    return None


async def list_analyses(owner_email: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if supabase_configured():
        query = f"select=*&owner_email=eq.{owner_email}&order=created_at_ts.desc"
        if project_id:
            query += f"&project_id=eq.{project_id}"
        rows = await supabase_select("analysis_results", query)
        return rows or []
    rows = [a for a in _ANALYSES.values() if a.get("owner_email") == owner_email]
    if project_id:
        rows = [a for a in rows if a.get("project_id") == project_id]
    return sorted(rows, key=lambda x: x.get("created_at_ts", 0), reverse=True)


def _report_archive_payload(owner_email: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a report archive row.

    The report archive is intentionally metadata-first. PDF/Excel binaries can be
    generated on demand from the saved dashboard payload or stored later in
    Supabase Storage/S3 by filling storage_bucket/storage_path.
    """
    dashboard = payload.get("dashboard") or payload.get("report_payload") or {}
    project_payload = dashboard.get("project") if isinstance(dashboard, dict) else {}
    project_payload = project_payload or {}
    report_id = payload.get("report_id") or project_payload.get("report_id") or new_report_id()
    print_size = str(payload.get("print_size") or "A4").upper()
    if print_size not in {"A4", "A3"}:
        print_size = "A4"
    return {
        "report_id": report_id,
        "owner_email": owner_email,
        "analysis_id": payload.get("analysis_id"),
        "project_id": payload.get("project_id") or project_payload.get("project_id"),
        "project_name": payload.get("project_name") or project_payload.get("name"),
        "analysis_type": payload.get("analysis_type") or project_payload.get("analysis_type") or "all",
        "report_type": payload.get("report_type") or "dashboard",
        "language": payload.get("language") or "en",
        "print_size": print_size,
        "print_orientation": payload.get("print_orientation") or ("landscape" if print_size == "A3" else "portrait"),
        "status": payload.get("status") or "archived",
        "title": payload.get("title") or payload.get("project_name") or project_payload.get("name") or "Project report",
        "dashboard": dashboard if isinstance(dashboard, dict) else {},
        "kpis": payload.get("kpis") or {},
        "report_payload": payload.get("report_payload") or {},
        "source": payload.get("source") or "analysis_save",
        "storage_bucket": payload.get("storage_bucket"),
        "storage_path": payload.get("storage_path"),
        "created_at_ts": payload.get("created_at_ts") or now_ts(),
    }


async def save_report_archive(owner_email: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    record = _report_archive_payload(owner_email, payload)
    if supabase_configured():
        saved = await supabase_insert("reports", record)
        return saved or record
    _REPORTS[record["report_id"]] = record
    return record


async def list_report_archive(owner_email: str, project_id: Optional[str] = None, analysis_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if supabase_configured():
        query = f"select=*&owner_email=eq.{owner_email}&order=created_at_ts.desc"
        if project_id:
            query += f"&project_id=eq.{project_id}"
        if analysis_id:
            query += f"&analysis_id=eq.{analysis_id}"
        rows = await supabase_select("reports", query)
        return rows or []
    rows = [r for r in _REPORTS.values() if r.get("owner_email") == owner_email]
    if project_id:
        rows = [r for r in rows if r.get("project_id") == project_id]
    if analysis_id:
        rows = [r for r in rows if r.get("analysis_id") == analysis_id]
    return sorted(rows, key=lambda x: x.get("created_at_ts", 0), reverse=True)


async def get_report_archive(owner_email: str, report_id: str) -> Optional[Dict[str, Any]]:
    if supabase_configured():
        rows = await supabase_select(
            "reports",
            f"select=*&report_id=eq.{report_id}&owner_email=eq.{owner_email}&limit=1",
        )
        return rows[0] if rows else None
    row = _REPORTS.get(report_id)
    if row and row.get("owner_email") == owner_email:
        return row
    return None


async def create_guest_result(payload: Dict[str, Any], ttl_days: int = 14) -> Dict[str, Any]:
    token = new_guest_token()
    record = {
        **payload,
        "guest_token": token,
        "expires_at_ts": now_ts() + ttl_days * 24 * 60 * 60,
        "created_at_ts": now_ts(),
    }
    if supabase_configured():
        saved = await supabase_insert("guest_orders", record)
        return saved or record
    _GUEST_RESULTS[token] = record
    return record


async def get_guest_result(token: str) -> Optional[Dict[str, Any]]:
    if supabase_configured():
        rows = await supabase_select("guest_orders", f"select=*&guest_token=eq.{token}&limit=1")
        row = rows[0] if rows else None
    else:
        row = _GUEST_RESULTS.get(token)
    if not row:
        return None
    if int(row.get("expires_at_ts") or 0) < now_ts():
        return None
    return row
