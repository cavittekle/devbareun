from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, local_store_enabled, require_project_owner
from .file_validation import validate_upload_metadata
from .production_store import ProductionStoreError, first_existing, first_update, insert_row, is_configured, select_rows, uuid_like
from .supabase_client import delete_storage_object, settings as supabase_settings, signed_upload_url


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class CreateUploadUrlRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    filename: str = Field(min_length=1, max_length=220)
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = Field(default=0, ge=0)


class MarkUploadedRequest(BaseModel):
    upload_id: Optional[str] = None
    file_id: Optional[str] = None
    project_id: str
    storage_path: str
    uploaded: bool = True
    checksum: Optional[str] = None


def _max_upload_bytes() -> int:
    if os.getenv("DEVBAREUN_MAX_UPLOAD_BYTES"):
        return int(os.getenv("DEVBAREUN_MAX_UPLOAD_BYTES", "104857600"))
    return int(os.getenv("DEVBAREUN_MAX_FILE_MB", "100")) * 1024 * 1024


def _storage_path(user: CurrentUser, project_id: str, upload_id: str, filename: str) -> str:
    safe_name = Path(filename).name.replace("\\", "_").replace("/", "_")
    return f"{user.auth_user_id}/{project_id}/{upload_id}/{safe_name}"


def _signed_url_to_absolute(raw: Dict[str, Any]) -> str:
    url = raw.get("signed_upload_url") or raw.get("signedUrl") or raw.get("signedURL") or raw.get("url") or raw.get("path")
    if not url:
        raise HTTPException(status_code=503, detail={"error": "storage_unavailable", "message": "Supabase did not return a signed upload URL."})
    if str(url).startswith("http"):
        return str(url)
    cfg = supabase_settings()
    relative = str(url)
    if relative.startswith("/storage/v1"):
        return f"{cfg.url}{relative}"
    if relative.startswith("/"):
        return f"{cfg.url}/storage/v1{relative}"
    return f"{cfg.url}/storage/v1/{relative}"


def _file_filters(file_id: str) -> list[Dict[str, Any]]:
    filters: list[Dict[str, Any]] = []
    if uuid_like(file_id):
        filters.append({"id": file_id})
    filters.append({"file_id": file_id})
    return filters


def _file_belongs_to_user(file_row: Dict[str, Any], user: CurrentUser) -> bool:
    if user.is_admin:
        return True
    candidates = {str(user.id).lower(), str(user.auth_user_id).lower(), str(user.email).lower()}
    owners = {
        str(file_row.get("user_id") or "").lower(),
        str(file_row.get("uploaded_by_user_id") or "").lower(),
        str(file_row.get("owner_email") or "").lower(),
    }
    return bool(candidates.intersection(owners))


def _find_file(file_id: str) -> Optional[Dict[str, Any]]:
    return first_existing("uploaded_files", _file_filters(file_id))


def _update_file(file_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if uuid_like(file_id):
        row = first_update("uploaded_files", {"id": file_id}, patch)
        if row:
            return row
    return first_update("uploaded_files", {"file_id": file_id}, patch)


def _local_upload_record(payload: CreateUploadUrlRequest, user: CurrentUser, meta: Dict[str, Any]) -> Dict[str, Any]:
    from .saas_store import insert

    upload_id = str(uuid4())
    storage_path = _storage_path(user, payload.project_id, upload_id, meta["original_filename"])
    row = insert("uploaded_files", {
        "id": upload_id,
        "file_id": upload_id,
        "user_id": user.auth_user_id,
        "project_id": payload.project_id,
        "bucket": os.getenv("SUPABASE_STORAGE_BUCKET", "project-files"),
        "storage_path": storage_path,
        "original_filename": meta["original_filename"],
        "file_ext": meta["file_ext"],
        "mime_type": meta["mime_type"],
        "size_bytes": meta["size_bytes"],
        "upload_status": "awaiting_upload",
        "parser_status": "pending",
        "owner_email": user.email,
        "status": "awaiting_upload",
    })
    return {
        "upload_id": upload_id,
        "file_id": upload_id,
        "bucket": row["bucket"],
        "storage_path": storage_path,
        "signed_upload_url": None,
        "expires_in": 0,
        "mode": "local_metadata_only",
        "file": row,
    }


@router.post("/create-url")
async def create_upload_url(
    payload: CreateUploadUrlRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    await require_project_owner(payload.project_id, current_user)
    try:
        meta = validate_upload_metadata(payload.filename, payload.mime_type, payload.size_bytes, _max_upload_bytes())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_upload", "message": str(exc)}) from exc

    if not is_configured():
        if local_store_enabled():
            return _local_upload_record(payload, current_user, meta)
        raise HTTPException(status_code=503, detail={"error": "storage_not_configured", "message": "Supabase Storage is not configured."})

    upload_id = str(uuid4())
    bucket = supabase_settings().storage_bucket
    path = _storage_path(current_user, payload.project_id, upload_id, meta["original_filename"])

    try:
        signed = signed_upload_url(path)
        absolute_url = _signed_url_to_absolute(signed)
        row = insert_row("uploaded_files", {
            "id": upload_id,
            "file_id": upload_id,
            "user_id": current_user.id if uuid_like(current_user.id) else current_user.auth_user_id,
            "project_id": payload.project_id,
            "bucket": bucket,
            "storage_bucket": bucket,
            "storage_path": path,
            "original_filename": meta["original_filename"],
            "original_name": meta["original_filename"],
            "file_ext": meta["file_ext"],
            "extension": meta["file_ext"],
            "mime_type": meta["mime_type"],
            "content_type": meta["mime_type"],
            "size_bytes": meta["size_bytes"],
            "file_size_bytes": meta["size_bytes"],
            "upload_status": "awaiting_upload",
            "parser_status": "pending",
            "status": "awaiting_upload",
            "owner_email": current_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        })
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload metadata could not be saved."}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "storage_unavailable", "message": "Signed upload URL could not be created."}) from exc

    return {
        "upload_id": upload_id,
        "file_id": upload_id,
        "bucket": bucket,
        "storage_path": path,
        "signed_upload_url": absolute_url,
        "expires_in": 3600,
        "file": row,
    }


@router.post("/mark-uploaded")
async def mark_uploaded(payload: MarkUploadedRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    await require_project_owner(payload.project_id, current_user)
    file_id = payload.upload_id or payload.file_id
    if not file_id:
        raise HTTPException(status_code=400, detail={"error": "invalid_upload", "message": "upload_id or file_id is required."})

    if not is_configured() and local_store_enabled():
        from .saas_store import find_one, update_one

        file_row = find_one("uploaded_files", file_id=file_id)
        if not file_row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
        if not _file_belongs_to_user(file_row, current_user):
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can update only your own upload."})
        updated = update_one("uploaded_files", "file_id", file_id, {
            "upload_status": "uploaded",
            "status": "uploaded",
            "checksum": payload.checksum,
            "updated_at": datetime.utcnow().isoformat(),
        })
        return {"file": updated or file_row}

    try:
        file_row = _find_file(file_id)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be loaded."}) from exc
    if not file_row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
    if not _file_belongs_to_user(file_row, current_user):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can update only your own upload."})
    if str(file_row.get("project_id")) != str(payload.project_id) or str(file_row.get("storage_path")) != str(payload.storage_path):
        raise HTTPException(status_code=400, detail={"error": "upload_mismatch", "message": "File/project/storage path mismatch."})

    patch = {
        "upload_status": "uploaded" if payload.uploaded else "awaiting_upload",
        "status": "uploaded" if payload.uploaded else "awaiting_upload",
        "parser_status": "pending",
        "checksum": payload.checksum,
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        updated = _update_file(file_id, patch)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be updated."}) from exc
    return {"file": updated or file_row}


@router.get("/project/{project_id}")
async def list_project_uploads(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    await require_project_owner(project_id, current_user)
    if not is_configured() and local_store_enabled():
        from .saas_store import list_rows

        rows = list_rows("uploaded_files", project_id=project_id)
        rows = [row for row in rows if str(row.get("status") or row.get("upload_status") or "").lower() != "deleted"]
        return {"project_id": project_id, "uploaded_files": rows}
    try:
        rows = select_rows("uploaded_files", {"project_id": project_id}, limit=500) if is_configured() else []
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project uploads could not be listed."}) from exc
    rows = [row for row in rows if str(row.get("status") or row.get("upload_status") or "").lower() != "deleted"]
    return {"project_id": project_id, "uploaded_files": rows}


@router.delete("/{file_id}")
async def delete_upload(file_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    if not is_configured() and local_store_enabled():
        from .saas_store import find_one, update_one

        file_row = find_one("uploaded_files", file_id=file_id)
        if not file_row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
        if not _file_belongs_to_user(file_row, current_user):
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can delete only your own upload."})
        updated = update_one("uploaded_files", "file_id", file_id, {
            "upload_status": "deleted",
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "storage_delete_status": "local_metadata_only",
        })
        return {"status": "deleted", "storage_delete_status": "local_metadata_only", "file": updated or file_row}

    try:
        file_row = _find_file(file_id)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be loaded."}) from exc
    if not file_row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
    if not _file_belongs_to_user(file_row, current_user):
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can delete only your own upload."})

    storage_delete_status = "not_requested"
    if file_row.get("storage_path"):
        try:
            delete_storage_object(file_row["storage_path"])
            storage_delete_status = "deleted"
        except Exception:
            storage_delete_status = "storage_delete_failed"
    patch = {
        "upload_status": "deleted",
        "status": "deleted",
        "deleted_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "storage_delete_status": storage_delete_status,
    }
    try:
        updated = _update_file(file_id, patch)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be deleted."}) from exc
    return {"status": "deleted", "storage_delete_status": storage_delete_status, "file": updated or file_row}
