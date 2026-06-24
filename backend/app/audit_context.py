"""Request-scoped audit context.

The context is deliberately limited to non-secret operational metadata. It is
used by the audit writer so event records can be correlated with API responses
without storing bearer tokens, cookies or request bodies.
"""
from __future__ import annotations

from contextvars import ContextVar, Token
import re
from typing import Any, Dict, Tuple
from uuid import uuid4

from fastapi import Request

_REQUEST_ID: ContextVar[str] = ContextVar("devbareun_request_id", default="")
_REQUEST_META: ContextVar[Dict[str, Any]] = ContextVar("devbareun_request_meta", default={})
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def _safe_text(value: str | None, limit: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:limit]


def begin_request_context(request: Request) -> Tuple[Token[str], Token[Dict[str, Any]], str]:
    """Set a bounded request context and return reset tokens.

    Caller-supplied request IDs are accepted only when they match a conservative
    syntax. Otherwise a server-generated UUID is used.
    """
    supplied = _safe_text(request.headers.get("x-request-id"), 128)
    request_id = supplied if supplied and _REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
    client = request.client.host if request.client else None
    meta = {
        "request_id": request_id,
        "request_method": _safe_text(request.method, 12),
        "request_path": _safe_text(request.url.path, 300),
        "ip_address": _safe_text(client, 80),
        "user_agent": _safe_text(request.headers.get("user-agent"), 512),
    }
    return _REQUEST_ID.set(request_id), _REQUEST_META.set(meta), request_id


def end_request_context(tokens: Tuple[Token[str], Token[Dict[str, Any]], str]) -> None:
    request_token, meta_token, _ = tokens
    _REQUEST_META.reset(meta_token)
    _REQUEST_ID.reset(request_token)


def current_audit_context() -> Dict[str, Any]:
    """Return a copy so callers cannot mutate the ContextVar payload."""
    return dict(_REQUEST_META.get() or {})


def current_request_id() -> str | None:
    value = _REQUEST_ID.get()
    return value or None
