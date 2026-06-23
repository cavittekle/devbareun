from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import re
from typing import Any, Dict, Iterable, List, Optional


class ProductionStoreError(RuntimeError):
    pass


def _settings() -> Dict[str, str]:
    return {
        "url": (os.getenv("SUPABASE_URL") or "").rstrip("/"),
        "service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "",
    }


def is_configured() -> bool:
    cfg = _settings()
    return bool(cfg["url"] and cfg["service_role_key"])


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    cfg = _settings()
    if not is_configured():
        raise ProductionStoreError("Supabase production store is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    headers = {
        "apikey": cfg["service_role_key"],
        "Authorization": f"Bearer {cfg['service_role_key']}",
        "Content-Type": "application/json",
    }
    headers.update(extra or {})
    return headers


def _url(path: str) -> str:
    cfg = _settings()
    return f"{cfg['url']}/rest/v1/{path.lstrip('/')}"


def _encode_filters(filters: Optional[Dict[str, Any]] = None) -> str:
    if not filters:
        return ""
    pairs: List[tuple[str, str]] = []
    for key, value in filters.items():
        if value is None:
            continue
        pairs.append((key, f"eq.{value}"))
    return urllib.parse.urlencode(pairs)


def _request(method: str, path: str, payload: Any = None, headers: Optional[Dict[str, str]] = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(_url(path), data=body, method=method.upper(), headers=_headers(headers))
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail: Any = json.loads(raw)
        except Exception:
            detail = raw
        raise ProductionStoreError(f"Supabase REST error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProductionStoreError(f"Supabase REST connection failed: {exc}") from exc


def select_rows(table: str, filters: Optional[Dict[str, Any]] = None, *, columns: str = "*", limit: int = 100) -> List[Dict[str, Any]]:
    query = [("select", columns), ("limit", str(max(1, min(limit, 1000))))]
    encoded = urllib.parse.urlencode(query)
    filter_query = _encode_filters(filters)
    path = f"{table}?{encoded}" + (f"&{filter_query}" if filter_query else "")
    data = _request("GET", path)
    return data if isinstance(data, list) else []


def select_one(table: str, filters: Dict[str, Any], *, columns: str = "*") -> Optional[Dict[str, Any]]:
    rows = select_rows(table, filters, columns=columns, limit=1)
    return rows[0] if rows else None


def insert_row(table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = _request("POST", table, payload, headers={"Prefer": "return=representation"})
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return payload


def call_rpc(function_name: str, payload: Dict[str, Any]) -> Any:
    """Call a PostgREST-exposed Supabase function with a safe identifier.

    The backend uses this for database-side atomic operations that cannot be
    represented safely as separate REST reads and updates.
    """
    name = str(function_name or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ProductionStoreError("RPC function name must be a safe SQL identifier.")
    return _request("POST", f"rpc/{name}", payload)


def upsert_row(table: str, payload: Dict[str, Any], *, on_conflict: str) -> Dict[str, Any]:
    """Insert or update one row using a declared unique key.

    This intentionally accepts only a simple column identifier for ``on_conflict``
    so operational callers cannot interpolate arbitrary PostgREST query strings.
    """
    key = str(on_conflict or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ProductionStoreError("Upsert requires a safe on_conflict column name.")
    data = _request(
        "POST",
        f"{table}?on_conflict={urllib.parse.quote(key, safe='')}",
        payload,
        headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return payload


def update_rows(table: str, filters: Dict[str, Any], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    filter_query = _encode_filters(filters)
    if not filter_query:
        raise ProductionStoreError("Update requires at least one filter.")
    data = _request("PATCH", f"{table}?{filter_query}", payload, headers={"Prefer": "return=representation"})
    return data if isinstance(data, list) else []


def first_update(table: str, filters: Dict[str, Any], payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = update_rows(table, filters, payload)
    return rows[0] if rows else None


def uuid_like(value: str) -> bool:
    text = str(value or "")
    return len(text) == 36 and text.count("-") == 4


def first_existing(table: str, filters_list: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for filters in filters_list:
        try:
            row = select_one(table, filters)
        except ProductionStoreError:
            raise
        if row:
            return row
    return None
