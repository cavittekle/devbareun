from __future__ import annotations

import os
import re
import time
import json
import urllib.error
import urllib.request
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def runtime_environment() -> str:
    return (
        os.getenv("DEVBAREUN_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("RAILWAY_ENVIRONMENT")
        or "development"
    ).strip().lower()


def is_production() -> bool:
    return runtime_environment() in {"production", "prod", "live"}


def production_security_enabled() -> bool:
    return bool_env("DEVBAREUN_PRODUCTION_SECURITY", is_production())


def admin_email_fallback_allowed() -> bool:
    # In production, admin access should come from verified Supabase user metadata
    # or the explicit DEVBAREUN_ADMIN_EMAILS allow-list, not broad email-domain logic.
    return bool_env("DEVBAREUN_ALLOW_ADMIN_EMAIL_FALLBACK", not is_production())


def devbareun_domain_admin_allowed() -> bool:
    return bool_env("DEVBAREUN_ALLOW_DEVBAREUN_DOMAIN_ADMINS", not is_production())


def mock_payment_allowed() -> bool:
    return bool_env("DEVBAREUN_ENABLE_MOCK_PAYMENT", False) and not production_security_enabled()


def require_production_secret(name: str) -> None:
    if production_security_enabled() and not os.getenv(name):
        raise HTTPException(status_code=503, detail=f"Production security requires {name} to be configured.")


class RateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _bucket(self, method: str, path: str) -> Tuple[str, int, int]:
        method = method.upper()
        p = path.lower()
        window = int_env("DEVBAREUN_RATE_LIMIT_WINDOW_SECONDS", 60)
        if p.startswith("/api/admin"):
            return "admin", int_env("DEVBAREUN_RATE_LIMIT_ADMIN_PER_MIN", 120), window
        if "/auth/" in p or p.endswith("/auth/me") or p.endswith("/login") or p.endswith("/register"):
            return "auth", int_env("DEVBAREUN_RATE_LIMIT_AUTH_PER_MIN", 20), window
        if "webhook" in p:
            return "webhook", int_env("DEVBAREUN_RATE_LIMIT_WEBHOOK_PER_MIN", 100), window
        if "upload" in p or "storage/create-upload-url" in p:
            return "upload", int_env("DEVBAREUN_RATE_LIMIT_UPLOAD_PER_MIN", 30), window
        if "analyze" in p or "analysis" in p:
            return "analysis", int_env("DEVBAREUN_RATE_LIMIT_ANALYSIS_PER_MIN", 20), window
        if "report/pdf" in p or "report/excel" in p or "create-download-url" in p:
            return "export", int_env("DEVBAREUN_RATE_LIMIT_EXPORT_PER_MIN", 60), window
        return "default", int_env("DEVBAREUN_RATE_LIMIT_DEFAULT_PER_MIN", 180), window

    def _check_upstash(self, key: str, bucket: str, limit: int, window: int) -> bool:
        url = (os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        if not url or not token:
            return False
        body = json.dumps([
            ["INCR", key],
            ["EXPIRE", key, window, "NX"],
        ]).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/pipeline",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if production_security_enabled():
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": "Rate limiter is temporarily unavailable.",
                        "bucket": bucket,
                    },
                ) from exc
            return False
        count = int(((payload or [{}])[0] or {}).get("result") or 0)
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Too many requests. Please retry shortly.",
                    "bucket": bucket,
                    "retry_after_seconds": window,
                },
                headers={"Retry-After": str(window)},
            )
        return True

    def _check_memory(self, key: str, bucket: str, limit: int, window: int) -> None:
        now = time.time()
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Too many requests. Please retry shortly.",
                    "bucket": bucket,
                    "retry_after_seconds": window,
                },
                headers={"Retry-After": str(window)},
            )
        hits.append(now)

    def check(self, request: Request) -> None:
        if not bool_env("DEVBAREUN_RATE_LIMIT_ENABLED", True):
            return
        path = request.url.path or "/"
        if path in {"/", "/health", "/api/health"}:
            return
        bucket, limit, window = self._bucket(request.method, path)
        if limit <= 0:
            return
        client = client_ip(request)
        key = f"{client}:{bucket}"
        if self._check_upstash(key, bucket, limit, window):
            return
        self._check_memory(key, bucket, limit, window)


rate_limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def apply_security_headers(response: Any) -> Any:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault(
        "Content-Security-Policy",
        os.getenv(
            "DEVBAREUN_CONTENT_SECURITY_POLICY",
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
        ),
    )
    if production_security_enabled():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
    return response


def safe_guest_ttl_days(requested_days: Optional[int]) -> int:
    default_days = int_env("DEVBAREUN_GUEST_RESULT_DAYS", 7 if production_security_enabled() else 14)
    max_days = int_env("DEVBAREUN_GUEST_RESULT_MAX_DAYS", 7 if production_security_enabled() else 30)
    try:
        days = int(requested_days or default_days)
    except Exception:
        days = default_days
    return max(1, min(days, max_days))


def validate_public_token(token: str, label: str = "token") -> str:
    value = (token or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{20,160}", value):
        raise HTTPException(status_code=404, detail=f"Invalid or expired {label}.")
    return value


def assert_storage_path_access(file_row: Optional[Dict[str, Any]], user_email: Optional[str], requested_path: str) -> Dict[str, Any]:
    if not file_row:
        raise HTTPException(status_code=404, detail="File record was not found or is not available for download.")
    if file_row.get("deleted_at") or str(file_row.get("status") or "").lower() in {"deleted", "rejected", "virus_rejected"}:
        raise HTTPException(status_code=410, detail="File is no longer available.")
    if file_row.get("storage_path") != requested_path:
        raise HTTPException(status_code=400, detail="File storage path mismatch.")
    owner = (file_row.get("owner_email") or "").strip().lower()
    requester = (user_email or "").strip().lower()
    if owner and requester and owner != requester:
        raise HTTPException(status_code=403, detail="You can only access files owned by your workspace.")
    if owner and not requester:
        raise HTTPException(status_code=401, detail="Authorization is required for protected file access.")
    return file_row
