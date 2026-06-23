from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user, local_store_enabled, require_project_owner
from .access_control import can_access_project_scope, is_staff_role
from .file_validation import normalize_sha256_checksum, validate_upload_metadata
from .production_store import ProductionStoreError, first_existing, first_update, insert_row, is_configured, select_rows, uuid_like
from .supabase_client import delete_storage_object, settings as supabase_settings, signed_upload_url
from .services.data_lifecycle_service import soft_delete_schedule
from .services.project_activity_service import record_project_activity
from .security_runtime import production_security_enabled


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _timeline(project: Dict[str, Any], actor: CurrentUser, action: str, file_row: Dict[str, Any] | None = None) -> None:
    row = file_row or {}
    try:
        record_project_activity(
            project,
            actor,
            action,
            "uploaded_file",
            str(row.get("id") or row.get("file_id") or "") or None,
            {
                "file_extension": row.get("extension") or row.get("file_ext"),
                "size_bytes": row.get("size_bytes") or row.get("file_size_bytes"),
                "checksum_status": row.get("checksum_status"),
                "security_scan_status": row.get("security_scan_status"),
            },
        )
    except Exception:
        return


class CreateUploadUrlRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    filename: str = Field(min_length=1, max_length=220)
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = Field(default=0, ge=0)
    checksum: Optional[str] = Field(default=None, max_length=64)


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


def _checksum_required() -> bool:
    raw = os.getenv("DEVBAREUN_REQUIRE_UPLOAD_CHECKSUM")
    if raw is not None:
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    return production_security_enabled()


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
    # Uploaded file objects are more sensitive than generic project metadata.
    # Only roles with the explicit uploads capability may cross tenant bounds.
    if is_staff_role(user.role):
        return can_access_project_scope(user.role, "uploads")
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


def _local_upload_record(payload: CreateUploadUrlRequest, user: CurrentUser, meta: Dict[str, Any], checksum: str | None = None) -> Dict[str, Any]:
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
        "checksum": checksum,
        "checksum_algorithm": "sha256" if checksum else None,
        "checksum_status": "pending_verification" if checksum else "not_provided",
        "security_scan_status": "pending",
        "security_scan_engine": None,
        "security_scan_findings": [],
        "quarantine_status": "pending_scan",
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
    project = await require_project_owner(payload.project_id, current_user, section="uploads")
    try:
        meta = validate_upload_metadata(payload.filename, payload.mime_type, payload.size_bytes, _max_upload_bytes())
        checksum = normalize_sha256_checksum(payload.checksum)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_upload", "message": str(exc)}) from exc
    if _checksum_required() and not checksum:
        raise HTTPException(status_code=400, detail={"error": "checksum_required", "message": "A SHA-256 checksum is required for production uploads."})

    if not is_configured():
        if local_store_enabled():
            response = _local_upload_record(payload, current_user, meta, checksum)
            _timeline(project, current_user, "upload.prepared", response.get("file"))
            return response
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
            "checksum": checksum,
            "checksum_algorithm": "sha256" if checksum else None,
            "checksum_status": "pending_verification" if checksum else "not_provided",
            "security_scan_status": "pending",
            "security_scan_engine": None,
            "security_scan_findings": [],
            "quarantine_status": "pending_scan",
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

    _timeline(project, current_user, "upload.prepared", row)
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
    project = await require_project_owner(payload.project_id, current_user, section="uploads")
    file_id = payload.upload_id or payload.file_id
    if not file_id:
        raise HTTPException(status_code=400, detail={"error": "invalid_upload", "message": "upload_id or file_id is required."})
    try:
        supplied_checksum = normalize_sha256_checksum(payload.checksum)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_checksum", "message": str(exc)}) from exc

    if not is_configured() and local_store_enabled():
        from .saas_store import find_one, update_one

        file_row = find_one("uploaded_files", file_id=file_id)
        if not file_row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
        if not _file_belongs_to_user(file_row, current_user):
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "You can update only your own upload."})
        expected_checksum = normalize_sha256_checksum(file_row.get("checksum"))
        if expected_checksum and supplied_checksum and expected_checksum != supplied_checksum:
            raise HTTPException(status_code=409, detail={"error": "checksum_conflict", "message": "Uploaded checksum does not match the checksum registered for this upload."})
        if _checksum_required() and not (expected_checksum or supplied_checksum):
            raise HTTPException(status_code=400, detail={"error": "checksum_required", "message": "This production upload requires a SHA-256 checksum."})
        updated = update_one("uploaded_files", "file_id", file_id, {
            "upload_status": "uploaded",
            "status": "uploaded",
            "checksum": expected_checksum or supplied_checksum,
            "checksum_algorithm": "sha256" if (expected_checksum or supplied_checksum) else None,
            "checksum_status": "pending_verification" if (expected_checksum or supplied_checksum) else "not_provided",
            "security_scan_status": "pending",
            "security_scan_engine": None,
            "security_scan_started_at": None,
            "security_scan_completed_at": None,
            "security_scan_error": None,
            "security_scan_findings": [],
            "quarantine_status": "pending_scan",
            "quarantine_reason": None,
            "quarantined_at": None,
            "updated_at": datetime.utcnow().isoformat(),
        })
        response_file = updated or file_row
        _timeline(project, current_user, "upload.completed", response_file)
        return {"file": response_file}

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
    expected_checksum = normalize_sha256_checksum(file_row.get("checksum"))
    if expected_checksum and supplied_checksum and expected_checksum != supplied_checksum:
        raise HTTPException(status_code=409, detail={"error": "checksum_conflict", "message": "Uploaded checksum does not match the checksum registered for this upload."})
    if _checksum_required() and not (expected_checksum or supplied_checksum):
        raise HTTPException(status_code=400, detail={"error": "checksum_required", "message": "This production upload requires a SHA-256 checksum."})

    patch = {
        "upload_status": "uploaded" if payload.uploaded else "awaiting_upload",
        "status": "uploaded" if payload.uploaded else "awaiting_upload",
        "parser_status": "pending",
        "checksum": expected_checksum or supplied_checksum,
        "checksum_algorithm": "sha256" if (expected_checksum or supplied_checksum) else None,
        "checksum_status": "pending_verification" if (expected_checksum or supplied_checksum) else "not_provided",
        "security_scan_status": "pending",
        "security_scan_engine": None,
        "security_scan_started_at": None,
        "security_scan_completed_at": None,
        "security_scan_error": None,
        "security_scan_findings": [],
        "quarantine_status": "pending_scan",
        "quarantine_reason": None,
        "quarantined_at": None,
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        updated = _update_file(file_id, patch)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be updated."}) from exc
    response_file = updated or file_row
    _timeline(project, current_user, "upload.completed", response_file)
    return {"file": response_file}


@router.get("/project/{project_id}")
async def list_project_uploads(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    await require_project_owner(project_id, current_user, section="uploads")
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
        project_id = str(file_row.get("project_id") or "")
        if not project_id:
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Upload is not linked to an accessible project."})
        project = await require_project_owner(project_id, current_user, section="uploads")
        updated = update_one("uploaded_files", "file_id", file_id, {
            "upload_status": "deleted",
            "status": "deleted",
            **soft_delete_schedule(),
            "updated_at": datetime.utcnow().isoformat(),
            "storage_delete_status": "local_metadata_only",
        })
        response_file = updated or file_row
        _timeline(project, current_user, "upload.deleted", response_file)
        return {"status": "deleted", "storage_delete_status": "local_metadata_only", "file": response_file}

    try:
        file_row = _find_file(file_id)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be loaded."}) from exc
    if not file_row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Upload record not found."})
    project_id = str(file_row.get("project_id") or "")
    if not project_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Upload is not linked to an accessible project."})
    project = await require_project_owner(project_id, current_user, section="uploads")

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
        **soft_delete_schedule(),
        "updated_at": datetime.utcnow().isoformat(),
        "storage_delete_status": storage_delete_status,
    }
    try:
        updated = _update_file(file_id, patch)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Upload record could not be deleted."}) from exc
    response_file = updated or file_row
    _timeline(project, current_user, "upload.deleted", response_file)
    return {"status": "deleted", "storage_delete_status": storage_delete_status, "file": response_file}
