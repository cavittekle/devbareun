from __future__ import annotations

import os
import re
import time
import json
import urllib.error
import urllib.request
import secrets
from urllib.parse import urlparse
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Tuple

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


def in_memory_rate_limit_allowed() -> bool:
    return bool_env("DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT", not production_security_enabled())


def require_production_secret(name: str) -> None:
    if production_security_enabled() and not os.getenv(name):
        raise HTTPException(status_code=503, detail=f"Production security requires {name} to be configured.")


AUTH_COOKIE_NAME = "devbareun_auth"
CSRF_COOKIE_NAME = "devbareun_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def csrf_token_required() -> bool:
    # Origin/Referer validation is always enforced for cookie-authenticated mutating
    # requests in production security mode. The double-submit token can be enabled
    # once all clients are updated, and is enabled by default in production.
    return bool_env("DEVBAREUN_REQUIRE_CSRF_TOKEN", production_security_enabled())


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def analysis_job_mode() -> str:
    mode = (os.getenv("DEVBAREUN_ANALYSIS_JOB_MODE") or "background").strip().lower()
    if mode not in {"background", "worker", "inline"}:
        return "background"
    return mode


def _env_status(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        return "missing"
    lowered = value.lower()
    if lowered.startswith("replace_") or "your-project" in lowered or "example" in lowered:
        return "placeholder"
    return "configured"


def set_csrf_cookie(response: Any, token: Optional[str] = None) -> str:
    value = token or new_csrf_token()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        value,
        httponly=False,
        secure=production_security_enabled(),
        samesite="none" if production_security_enabled() else "lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return value


def clear_csrf_cookie(response: Any) -> None:
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def production_frontend_origins() -> Tuple[str, ...]:
    return (
        "https://devbareun.com",
        "https://www.devbareun.com",
        "https://devbareun.vercel.app",
    )


def configured_allowed_origins() -> set[str]:
    raw = os.getenv("DEVBAREUN_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS") or ""
    values = {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}
    if production_security_enabled():
        values = {origin for origin in values if origin != "*" and not origin.startswith("http://")}
        return values or set(production_frontend_origins())
    return values or {
        *production_frontend_origins(),
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    }


def _origin_from_referer(value: str) -> str:
    parsed = urlparse(value or "")
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _request_origin(request: Request) -> str:
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin:
        return origin
    return _origin_from_referer(request.headers.get("referer") or "")


def _is_webhook_path(path: str) -> bool:
    lowered = (path or "").lower()
    return "webhook" in lowered


def enforce_cookie_request_integrity(request: Request) -> None:
    """Protect HTTP-only cookie sessions from cross-site mutating requests.

    Server-to-server endpoints such as payment webhooks are intentionally excluded.
    Bearer-token API clients are not forced to send CSRF tokens unless they also send
    the auth cookie.
    """
    method = (request.method or "GET").upper()
    if method in SAFE_HTTP_METHODS or _is_webhook_path(request.url.path):
        return

    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if not auth_cookie:
        return

    origin = _request_origin(request)
    if production_security_enabled() and not origin:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "origin_required",
                "message": "Cookie-authenticated state-changing requests require an Origin or Referer header.",
            },
        )
    if origin and origin not in configured_allowed_origins():
        raise HTTPException(
            status_code=403,
            detail={
                "error": "origin_not_allowed",
                "message": "Request origin is not allowed for cookie-authenticated changes.",
            },
        )

    if not csrf_token_required():
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    header_token = request.headers.get(CSRF_HEADER_NAME) or request.headers.get("x-xsrf-token") or ""
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "csrf_failed",
                "message": "CSRF token is missing or invalid.",
            },
        )


def runtime_readiness() -> Dict[str, Any]:
    """Return secret-safe production readiness flags for health checks."""
    from .telemetry import error_telemetry_status
    from .services.data_lifecycle_service import policy_from_env
    upstash_ready = bool(os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN"))
    lemon_required = (
        "LEMON_SQUEEZY_API_KEY",
        "LEMON_SQUEEZY_STORE_ID",
        "LEMON_SQUEEZY_WEBHOOK_SECRET",
        "LEMON_SQUEEZY_SINGLE_VARIANT_ID",
        "LEMON_SQUEEZY_PLUS_VARIANT_ID",
        "LEMON_SQUEEZY_PRO_VARIANT_ID",
    )
    lemon_ready = all(_env_status(name) == "configured" for name in lemon_required)
    supabase_public_ready = _env_status("SUPABASE_URL") == "configured" and _env_status("SUPABASE_ANON_KEY") == "configured"
    supabase_private_ready = _env_status("SUPABASE_URL") == "configured" and _env_status("SUPABASE_SERVICE_ROLE_KEY") == "configured"
    telemetry = error_telemetry_status()
    try:
        data_lifecycle = policy_from_env().as_dict()
        data_lifecycle_status = "configured"
    except ValueError:
        data_lifecycle = {}
        data_lifecycle_status = "invalid"
    return {
        "environment": runtime_environment(),
        "production_security": production_security_enabled(),
        "csrf_token": "required" if csrf_token_required() else "not_required",
        "analysis_job_mode": analysis_job_mode(),
        "upload_security_screening": "heuristic",
        "block_macro_enabled_uploads": "enabled" if bool_env("DEVBAREUN_BLOCK_MACRO_ENABLED_UPLOADS", False) else "disabled",
        "block_active_pdf_content": "enabled" if bool_env("DEVBAREUN_BLOCK_ACTIVE_PDF_CONTENT", False) else "disabled",
        "dev_auth": "enabled" if bool_env("DEVBAREUN_ENABLE_DEV_AUTH", False) else "disabled",
        "local_store": "enabled" if bool_env("DEVBAREUN_ENABLE_LOCAL_STORE", False) else "disabled",
        "mock_payment": "enabled" if bool_env("DEVBAREUN_ENABLE_MOCK_PAYMENT", False) else "disabled",
        "pilot_login": "enabled" if bool_env("DEVBAREUN_ENABLE_PILOT_LOGIN", False) else "disabled",
        "pilot_checkout": "enabled" if bool_env("DEVBAREUN_ENABLE_PILOT_CHECKOUT", False) else "disabled",
        "legacy_project_routes": "enabled" if bool_env("DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES", False) else "disabled",
        "ephemeral_upload": "enabled" if bool_env("DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD", False) else "disabled",
        "docs": "disabled" if bool_env("DEVBAREUN_DISABLE_DOCS", False) else "enabled",
        "supabase_public": "configured" if supabase_public_ready else "missing",
        "supabase_private": "configured" if supabase_private_ready else "missing",
        "supabase_storage_bucket": os.getenv("SUPABASE_STORAGE_BUCKET") or "project-files",
        "payment_provider": os.getenv("DEVBAREUN_PAYMENT_PROVIDER") or "lemonsqueezy",
        "lemonsqueezy": "configured" if lemon_ready else "missing",
        "rate_limit": "upstash" if upstash_ready else ("in_memory_allowed" if in_memory_rate_limit_allowed() else "missing_upstash"),
        "error_telemetry": telemetry.get("mode"),
        "error_telemetry_required": telemetry.get("required") is True,
        "error_telemetry_external": "configured" if telemetry.get("external_configured") is True else "not_configured",
        "structured_logging": telemetry.get("structured_logging"),
        "data_lifecycle": data_lifecycle_status,
        "data_lifecycle_auto_purge": data_lifecycle.get("auto_purge_enabled") if data_lifecycle else None,
    }


def runtime_readiness_issues() -> Dict[str, List[str]]:
    """Return secret-safe release-blocking errors and deploy warnings."""
    readiness = runtime_readiness()
    errors: List[str] = []
    warnings: List[str] = []

    if readiness["environment"] in {"production", "prod", "live"}:
        if not readiness["production_security"]:
            errors.append("DEVBAREUN_PRODUCTION_SECURITY must be true in production.")
        for flag in ("dev_auth", "local_store", "mock_payment", "pilot_login", "pilot_checkout", "legacy_project_routes", "ephemeral_upload"):
            if readiness.get(flag) != "disabled":
                errors.append(f"{flag} must be disabled in production.")
        if readiness.get("docs") != "disabled":
            warnings.append("DEVBAREUN_DISABLE_DOCS should be true in production.")
        if readiness.get("csrf_token") != "required":
            errors.append("DEVBAREUN_REQUIRE_CSRF_TOKEN should be true in production.")
        if readiness.get("rate_limit") != "upstash":
            errors.append("Upstash rate limiting must be configured or explicitly accepted for pilot operation.")
        if readiness.get("supabase_private") != "configured":
            errors.append("Supabase private/service configuration is missing.")
        if readiness.get("lemonsqueezy") != "configured":
            errors.append("Lemon Squeezy production configuration is incomplete.")
        if readiness.get("analysis_job_mode") != "worker":
            warnings.append("DEVBAREUN_ANALYSIS_JOB_MODE=worker is recommended for production.")
        if readiness.get("data_lifecycle") != "configured":
            errors.append("Data lifecycle retention policy is invalid.")
        if readiness.get("data_lifecycle_auto_purge") is True:
            warnings.append("Automatic physical purge is declared enabled; verify a separately reviewed purge operator exists before production use.")
        if readiness.get("error_telemetry_required") and readiness.get("error_telemetry_external") != "configured":
            errors.append("External error telemetry is required but not configured.")
        elif readiness.get("error_telemetry") == "disabled":
            warnings.append("Error telemetry is disabled; only provider logs will remain available.")

    return {"errors": errors, "warnings": warnings}


def runtime_readiness_report() -> Dict[str, Any]:
    issues = runtime_readiness_issues()
    return {
        "ready": not issues["errors"],
        "readiness": runtime_readiness(),
        "errors": issues["errors"],
        "warnings": issues["warnings"],
    }


class RateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _bucket(self, method: str, path: str) -> Tuple[str, int, int]:
        method = method.upper()
        p = path.lower()
        window = int_env("DEVBAREUN_RATE_LIMIT_WINDOW_SECONDS", 60)
        if p.startswith("/api/admin") or p.startswith("/api/super-admin"):
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
        if path in {"/", "/health", "/api/health", "/api/version"}:
            return
        bucket, limit, window = self._bucket(request.method, path)
        if limit <= 0:
            return
        client = client_ip(request)
        key = f"{client}:{bucket}"
        if self._check_upstash(key, bucket, limit, window):
            return
        if production_security_enabled() and not in_memory_rate_limit_allowed():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "rate_limiter_not_configured",
                    "message": "Production rate limiting requires Upstash Redis or an explicit in-memory override.",
                    "bucket": bucket,
                },
            )
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
