from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class SupabaseConfigError(RuntimeError):
    pass


@dataclass
class SupabaseSettings:
    url: str
    anon_key: str | None
    service_role_key: str | None
    storage_bucket: str


def settings() -> SupabaseSettings:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "project-files")
    return SupabaseSettings(url=url, anon_key=anon_key, service_role_key=service_role_key, storage_bucket=storage_bucket)


def is_configured(require_service: bool = False) -> bool:
    cfg = settings()
    if not cfg.url:
        return False
    if require_service:
        return bool(cfg.service_role_key)
    return bool(cfg.anon_key or cfg.service_role_key)


def _headers(token: str | None = None, service: bool = False) -> Dict[str, str]:
    cfg = settings()
    key = cfg.service_role_key if service else (cfg.anon_key or cfg.service_role_key)
    if not cfg.url or not key:
        raise SupabaseConfigError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_SERVICE_ROLE_KEY.")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {token or key}",
        "Content-Type": "application/json",
    }
    return headers


def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None, token: str | None = None, service: bool = False) -> Dict[str, Any]:
    cfg = settings()
    if not cfg.url:
        raise SupabaseConfigError("SUPABASE_URL is not configured.")
    url = f"{cfg.url}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=_headers(token=token, service=service))
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail: Any = json.loads(raw)
        except Exception:
            detail = raw
        raise RuntimeError(f"Supabase API error {exc.code}: {detail}") from exc


def get_user_from_token(access_token: str) -> Dict[str, Any]:
    """Validate a Supabase Auth access token and return the auth user payload."""
    if not access_token:
        raise RuntimeError("Missing Supabase access token.")
    return _request("GET", "/auth/v1/user", token=access_token, service=False)


def sign_up(email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"email": email, "password": password, "data": metadata or {}}
    try:
        return _request("POST", "/auth/v1/signup", payload, service=False)
    except Exception as public_signup_error:
        raise RuntimeError("Supabase public signup failed. Check Auth settings and email confirmation configuration.") from public_signup_error


def sign_in(email: str, password: str) -> Dict[str, Any]:
    return _request("POST", "/auth/v1/token?grant_type=password", {"email": email, "password": password}, service=False)


def storage_object_path(project_id: str, file_id: str, filename: str) -> str:
    safe = filename.replace("\\", "_").replace("/", "_").strip() or "uploaded_file"
    return f"projects/{project_id}/{file_id}/{safe}"


def signed_upload_url(path: str) -> Dict[str, Any]:
    """Create a signed upload URL through Supabase Storage using service role key."""
    cfg = settings()
    encoded = urllib.parse.quote(path, safe="")
    return _request("POST", f"/storage/v1/object/upload/sign/{cfg.storage_bucket}/{encoded}", {}, service=True)


def signed_download_url(path: str, expires_in: int = 3600) -> Dict[str, Any]:
    cfg = settings()
    encoded = urllib.parse.quote(path, safe="")
    return _request("POST", f"/storage/v1/object/sign/{cfg.storage_bucket}/{encoded}", {"expiresIn": expires_in}, service=True)


def delete_storage_object(path: str) -> Dict[str, Any]:
    """Delete one private Supabase Storage object using the backend service-role key."""
    cfg = settings()
    return _request("DELETE", f"/storage/v1/object/{cfg.storage_bucket}", {"prefixes": [path]}, service=True)
