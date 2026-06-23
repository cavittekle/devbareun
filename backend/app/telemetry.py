"""Privacy-safe structured error telemetry for DevBareun.

The module always emits bounded JSON events to process stdout.  It can also send
safe, synthetic error notifications to Sentry when explicitly configured.  Raw
request bodies, file contents, cookies, tokens, provider secrets and original
exception messages are deliberately excluded from external telemetry.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

from .audit_context import current_request_id
from .version import APP_VERSION

_LOGGER = logging.getLogger("devbareun")
_CONFIGURED_SERVICES: set[str] = set()
_SENTRY_INITIALIZED = False
_SENTRY_READY = False

_SECRET_KEY_RE = re.compile(r"(authorization|cookie|token|secret|password|api[_-]?key|dsn|session|signed|credential)", re.I)
_SECRET_VALUE_RE = re.compile(r"(?:sk-|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.|bearer\s+|token=|password=)", re.I)
_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def telemetry_mode() -> str:
    mode = (os.getenv("DEVBAREUN_ERROR_TELEMETRY_MODE") or "log").strip().lower()
    return mode if mode in {"log", "sentry", "disabled"} else "log"


def telemetry_required() -> bool:
    return _bool_env("DEVBAREUN_REQUIRE_ERROR_TELEMETRY", False)


def request_logs_enabled() -> bool:
    return _bool_env("DEVBAREUN_REQUEST_LOGS_ENABLED", True)


def _sentry_dsn() -> str:
    return (os.getenv("DEVBAREUN_SENTRY_DSN") or "").strip()


def _sentry_sdk_available() -> bool:
    return importlib.util.find_spec("sentry_sdk") is not None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_text(value: Any, limit: int = 256) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if _SECRET_VALUE_RE.search(text):
        return "[REDACTED]"
    return text[:limit]


def sanitize_metadata(value: Any, *, depth: int = 0) -> Any:
    """Return JSON-safe metadata with sensitive values removed and bounded."""
    if depth >= 4:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, Mapping):
        clean: Dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = _bounded_text(raw_key, 80)
            if not _SAFE_KEY_RE.fullmatch(key):
                key = "invalid_key"
            clean[key] = "[REDACTED]" if _SECRET_KEY_RE.search(key) else sanitize_metadata(raw_value, depth=depth + 1)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [sanitize_metadata(item, depth=depth + 1) for item in list(value)[:30]]
    return _bounded_text(value)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting exercised through event helpers
        payload: Dict[str, Any] = {
            "timestamp": _utc_now(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": _bounded_text(record.getMessage(), 300),
        }
        event = getattr(record, "devbareun_event", None)
        if event:
            payload["event"] = _bounded_text(event, 120)
        metadata = getattr(record, "devbareun_metadata", None)
        if isinstance(metadata, Mapping):
            payload.update(sanitize_metadata(metadata))
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _configure_logger() -> None:
    if any(getattr(handler, "_devbareun_structured", False) for handler in _LOGGER.handlers):
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler._devbareun_structured = True  # type: ignore[attr-defined]
    handler.setFormatter(_JsonFormatter())
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False


def _configure_sentry(service_name: str) -> None:
    global _SENTRY_INITIALIZED, _SENTRY_READY
    if _SENTRY_INITIALIZED:
        return
    _SENTRY_INITIALIZED = True
    if telemetry_mode() != "sentry" or not _sentry_dsn() or not _sentry_sdk_available():
        return
    try:
        import sentry_sdk  # type: ignore

        # Default integrations are intentionally disabled.  DevBareun sends only
        # synthetic, sanitized messages below, rather than raw request/exception
        # payloads that could contain customer or provider data.
        sentry_sdk.init(
            dsn=_sentry_dsn(),
            environment=(os.getenv("DEVBAREUN_ENV") or os.getenv("APP_ENV") or "development").strip(),
            release=f"devbareun@{APP_VERSION}",
            send_default_pii=False,
            default_integrations=False,
            traces_sample_rate=0.0,
        )
        _SENTRY_READY = True
        log_event("telemetry_sentry_initialized", service=service_name, telemetry_provider="sentry")
    except Exception:
        _SENTRY_READY = False
        log_event("telemetry_sentry_unavailable", level=logging.ERROR, service=service_name, error_type="TelemetryProviderInitializationError")


def configure_telemetry(service_name: str = "api") -> None:
    """Configure process-safe structured logging and optional external telemetry."""
    _configure_logger()
    _configure_sentry(service_name)
    if service_name not in _CONFIGURED_SERVICES:
        _CONFIGURED_SERVICES.add(service_name)
        log_event("telemetry_configured", service=service_name, telemetry_mode=telemetry_mode())


def log_event(event: str, *, level: int = logging.INFO, **metadata: Any) -> None:
    safe = sanitize_metadata(metadata)
    if isinstance(safe, dict):
        safe.setdefault("request_id", current_request_id())
        safe.setdefault("release", APP_VERSION)
    _LOGGER.log(level, event, extra={"devbareun_event": event, "devbareun_metadata": safe})


def capture_exception(exc: BaseException, *, event: str, service: str, **metadata: Any) -> None:
    """Capture a safe error signal without serializing the original exception text."""
    safe_metadata = {
        **metadata,
        "service": service,
        "error_type": exc.__class__.__name__,
        "request_id": current_request_id(),
    }
    log_event(event, level=logging.ERROR, **safe_metadata)
    if not _SENTRY_READY:
        return
    try:
        import sentry_sdk  # type: ignore

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("service", service)
            scope.set_tag("error_type", exc.__class__.__name__)
            scope.set_tag("release", APP_VERSION)
            if current_request_id():
                scope.set_tag("request_id", current_request_id())
            scope.set_context("devbareun", sanitize_metadata(safe_metadata))
            # A sanitized synthetic message is intentional: raw exception payloads
            # can contain provider or customer data.
            sentry_sdk.capture_message(f"{event}:{exc.__class__.__name__}", level="error")
    except Exception:
        log_event("telemetry_delivery_failed", level=logging.ERROR, service=service, error_type="TelemetryDeliveryError")


def error_telemetry_status() -> Dict[str, Any]:
    mode = telemetry_mode()
    dsn_present = bool(_sentry_dsn())
    sdk_available = _sentry_sdk_available()
    external_configured = bool(mode == "sentry" and dsn_present and sdk_available)
    return {
        "mode": mode,
        "required": telemetry_required(),
        "structured_logging": "enabled",
        "request_logs": "enabled" if request_logs_enabled() else "disabled",
        "external_provider": "sentry" if mode == "sentry" else None,
        "external_configured": external_configured,
        "sdk_available": sdk_available if mode == "sentry" else None,
        "release": APP_VERSION,
    }
