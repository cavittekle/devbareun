from __future__ import annotations

import os
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .analysis_types import PREMIUM_ANALYSIS_TYPE, normalize_analysis_type
from .audit_context import begin_request_context, current_request_id, end_request_context
from .auth_routes import router as auth_router
from .billing_routes import router as billing_router
from .dashboard_routes import router as dashboard_router
from .company_team_routes import router as company_team_router
from .project_sharing_routes import router as project_sharing_router
from .project_activity_routes import router as project_activity_router
from .data_lifecycle_routes import router as data_lifecycle_router
from .analysis_routes import router as analysis_router
from .legacy_routes import router as legacy_router
from .operations_routes import router as operations_router
from .persistence_routes import router as persistence_router
from .production_store import is_configured as production_store_configured
from .report_routes import router as report_router
from .saas_routes import router as saas_router
from .security_runtime import apply_security_headers, bool_env, enforce_cookie_request_integrity, production_security_enabled, rate_limiter, runtime_readiness, runtime_readiness_report
from .supabase_client import is_configured as supabase_is_configured
from .template_manifest import TEMPLATE_MANIFEST
from .telemetry import capture_exception, configure_telemetry, log_event, request_logs_enabled
from .upload_routes import router as upload_router
from .version import APP_VERSION

BASE_DIR = Path(__file__).resolve().parent.parent


def _production_origins() -> List[str]:
    return [
        "https://devbareun.com",
        "https://www.devbareun.com",
        "https://devbareun.vercel.app",
    ]


def _allowed_origins() -> List[str]:
    raw = os.getenv("DEVBAREUN_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS")
    if raw:
        values = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        if production_security_enabled():
            values = [origin for origin in values if origin != "*" and not origin.startswith("http://")]
            return values or _production_origins()
        return values or ["http://localhost:3000"]
    if production_security_enabled():
        return _production_origins()
    return [
        "https://devbareun.com",
        "https://www.devbareun.com",
        "https://devbareun.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://localhost:8000",
    ]


def _api_docs_enabled() -> bool:
    return not bool_env("DEVBAREUN_DISABLE_DOCS", production_security_enabled())


def _error_payload(code: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "error": True,
        "code": code,
        "message": message,
        "request_id": current_request_id(),
        "details": details or {},
    }


app = FastAPI(
    title="DevBareun Construction Analytics Backend",
    version=APP_VERSION,
    description="Production SaaS backend for construction file parsing, project dashboard generation and report exports.",
    docs_url="/docs" if _api_docs_enabled() else None,
    redoc_url="/redoc" if _api_docs_enabled() else None,
    openapi_url="/openapi.json" if _api_docs_enabled() else None,
)

configure_telemetry(service_name="api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def devbareun_security_middleware(request: Request, call_next):
    context_tokens = begin_request_context(request)
    request_id = context_tokens[2]
    started = perf_counter()
    response = None
    try:
        try:
            enforce_cookie_request_integrity(request)
            rate_limiter.check(request)
        except HTTPException as exc:
            detail = exc.detail
            code = f"http_{exc.status_code}"
            message = str(detail or "Request failed.")
            details: Dict[str, Any] = {}
            if isinstance(detail, dict):
                code = str(detail.get("code") or detail.get("error") or code)
                message = str(detail.get("message") or detail.get("detail") or "Request failed.")
                details = {k: v for k, v in detail.items() if k not in {"code", "error", "message", "detail"}}
            response = JSONResponse(status_code=exc.status_code, content=_error_payload(code, message, details), headers=exc.headers)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:  # pragma: no cover - exact route failures vary by deployment
                capture_exception(
                    exc,
                    event="api_unhandled_exception",
                    service="api",
                    method=request.method,
                    path=request.url.path,
                )
                response = JSONResponse(
                    status_code=500,
                    content=_error_payload("internal_error", "An unexpected server error occurred."),
                )
        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if response.status_code >= 500:
            log_event(
                "api_server_error_response",
                level=40,
                service="api",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        elif request_logs_enabled():
            log_event(
                "api_request_completed",
                service="api",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        return apply_security_headers(response)
    finally:
        end_request_context(context_tokens)


@app.exception_handler(StarletteHTTPException)
async def devbareun_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    code = f"http_{exc.status_code}"
    message = "Request failed."
    details: Dict[str, Any] = {}
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("detail") or message)
        code = str(detail.get("code") or detail.get("error") or code)
        details = {k: v for k, v in detail.items() if k not in {"message", "detail", "code", "error"}}
    elif detail:
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(code, message, details),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def devbareun_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_payload("validation_failed", "Request validation failed.", {"errors": exc.errors()}),
    )


# Canonical production route families. Keep router registration centralized here;
# route implementation lives in dedicated modules.
app.include_router(saas_router)
app.include_router(auth_router)
app.include_router(persistence_router)
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(operations_router)
app.include_router(dashboard_router)
app.include_router(company_team_router)
app.include_router(project_sharing_router)
app.include_router(project_activity_router)
app.include_router(data_lifecycle_router)
app.include_router(billing_router)
app.include_router(report_router)
app.include_router(legacy_router)


def _health_payload() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "DevBareun Backend",
        "database": "connected" if production_store_configured() else "not_configured",
        "storage": "configured" if supabase_is_configured(require_service=True) else "not_configured",
        "readiness": runtime_readiness(),
        "version": APP_VERSION,
        "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.get("/")
def root() -> Dict[str, Any]:
    return _health_payload()


@app.get("/health")
def health_public() -> Dict[str, Any]:
    return _health_payload()


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return _health_payload()


@app.get("/api/version")
def version() -> Dict[str, Any]:
    return {
        "service": "DevBareun Backend",
        "version": APP_VERSION,
        "environment": os.getenv("DEVBAREUN_ENV") or os.getenv("APP_ENV") or "development",
        "production_security": production_security_enabled(),
    }


@app.get("/api/readiness")
def readiness() -> Dict[str, Any]:
    return {
        "service": "DevBareun Backend",
        "version": APP_VERSION,
        **runtime_readiness_report(),
    }


@app.get("/api/templates")
def list_templates() -> Dict[str, Any]:
    base = "templates"
    return {
        "version": APP_VERSION,
        "templates": {
            key: {**value, "download_path": f"/{base}/{value['file']}", "api_download_path": f"/api/templates/{key}/download"}
            for key, value in TEMPLATE_MANIFEST.items()
        },
    }


@app.get("/api/templates/{analysis_type}/download")
def download_template(analysis_type: str) -> FileResponse:
    key = normalize_analysis_type(analysis_type)
    if key not in TEMPLATE_MANIFEST:
        key = PREMIUM_ANALYSIS_TYPE
    template_file = BASE_DIR.parent / "frontend" / "templates" / TEMPLATE_MANIFEST[key]["file"]
    if not template_file.exists():
        raise HTTPException(status_code=404, detail="Template file was not found.")
    return FileResponse(
        template_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=TEMPLATE_MANIFEST[key]["file"],
    )
