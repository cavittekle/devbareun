from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Cookie, File, Header, Request, Response, UploadFile

from .saas_common import *
from .services.data_lifecycle_service import soft_delete_schedule

router = APIRouter(prefix="/api", tags=["SaaS core"] )


class ProjectUpdateRequest(BaseModel):
    project_name: Optional[str] = None
    location: Optional[str] = None
    contractor: Optional[str] = None
    client: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_value: Optional[float] = None
    currency: Optional[str] = None
    project_status: Optional[str] = None
    analysis_type: Optional[str] = None

@router.get("/saas/health")
def saas_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "module": "saas-foundation",
        "version": APP_VERSION,
        "plans": PLAN_LIMITS,
        "supabase_configured": supabase_is_configured(),
        "storage_bucket": supabase_settings().storage_bucket,
        "readiness": runtime_readiness(),
    }

@router.post("/auth/supabase/register")
def supabase_register(payload: SupabaseAuthRequest) -> Dict[str, Any]:
    if not supabase_is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    try:
        auth_payload = sign_up(str(payload.email), payload.password, {"company_name": payload.company_name, "contact_person": payload.contact_person})
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "signup_failed", "message": "Registration could not be completed. Check the email and try again."}) from exc
    user = find_one("users", email=str(payload.email))
    if not user:
        user = insert("users", {
            "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
            "email": str(payload.email),
            "auth_provider": "supabase",
            "status": "pending_email_confirmation",
            "role": "customer",
        })
    company = None
    if payload.company_name and not find_one("companies", email=str(payload.email)):
        company = insert("companies", {
            "company_id": make_public_id("company"),
            "company_name": payload.company_name,
            "contact_person": payload.contact_person,
            "email": str(payload.email),
            "subscription_plan": "free",
        })
    log_activity(str(payload.email), "auth.supabase_register", {"user_id": user.get("user_id")})
    return {"status": "supabase_signup_started", "auth": auth_payload, "user": user, "company": company}

@router.post("/auth/supabase/login")
def supabase_login(payload: SupabaseAuthRequest, response: Response) -> Dict[str, Any]:
    if not supabase_is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    try:
        auth_payload = sign_in(str(payload.email), payload.password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail={"error": "login_failed", "message": "Email or password is incorrect."}) from exc
    _set_auth_cookie(response, (auth_payload.get("auth") or auth_payload).get("access_token"))
    user_payload = auth_payload.get("user") or {}
    local_user = _upsert_local_user_from_supabase(user_payload or {"email": str(payload.email)})
    return {"status": "authenticated", "auth": auth_payload, "user": local_user}

@router.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_session(authorization, auth_cookie)
    local_user = _upsert_local_user_from_supabase(auth_user)
    return {"auth_user": auth_user, "user": local_user}

@router.post("/storage/create-upload-url")
def create_storage_upload_url(payload: StorageSignRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_session(authorization, auth_cookie)
    user = _upsert_local_user_from_supabase(auth_user)
    project = find_one("projects", project_id=payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    owner_email = project.get("owner_email") or user.get("email")
    if project.get("owner_email") is None:
        project = update_one("projects", "project_id", payload.project_id, {"owner_email": owner_email}) or project
    if owner_email and owner_email != user.get("email"):
        raise HTTPException(status_code=403, detail="You can only upload files to your own project.")
    file_id = make_public_id("file")
    path = storage_object_path(payload.project_id, file_id, payload.file_name)
    try:
        signed = signed_upload_url(path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "storage_unavailable", "message": "Signed upload URL could not be created."}) from exc
    file_row = insert("uploaded_files", {
        "file_id": file_id,
        "project_id": payload.project_id,
        "owner_email": user.get("email"),
        "original_name": payload.file_name,
        "content_type": payload.content_type,
        "size_bytes": payload.size_bytes,
        "storage_provider": "supabase_storage",
        "storage_bucket": supabase_settings().storage_bucket,
        "storage_path": path,
        "status": "awaiting_upload",
        "upload_progress": 0,
    })
    log_activity(user.get("email"), "file.signed_upload_url_created", {"project_id": payload.project_id, "file_id": file_id})
    return {"file": file_row, "upload": signed}

@router.post("/storage/mark-uploaded")
def mark_storage_uploaded(payload: StorageUploadCompleteRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_session(authorization, auth_cookie)
    user = _upsert_local_user_from_supabase(auth_user)
    file_row = find_one("uploaded_files", file_id=payload.file_id)
    if not file_row:
        raise HTTPException(status_code=404, detail="File record not found.")
    _assert_file_owner(file_row, user)
    if file_row.get("project_id") != payload.project_id or file_row.get("storage_path") != payload.storage_path:
        raise HTTPException(status_code=400, detail="File/project/storage path mismatch.")
    updated = update_one("uploaded_files", "file_id", payload.file_id, {
        "status": "uploaded",
        "upload_progress": 100,
        "uploaded_at": datetime.utcnow().isoformat(),
        "checksum": payload.checksum,
    })
    log_activity(user.get("email"), "file.upload_completed", {"project_id": payload.project_id, "file_id": payload.file_id})
    return {"file": updated}

@router.post("/storage/create-download-url")
def create_storage_download_url(payload: StorageDownloadRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    auth_user = _supabase_user_from_session(authorization, auth_cookie)
    user = _upsert_local_user_from_supabase(auth_user)
    file_row = find_one("uploaded_files", storage_path=payload.storage_path)
    assert_storage_path_access(file_row, user.get("email"), payload.storage_path)
    try:
        signed = signed_download_url(payload.storage_path, payload.expires_in)
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "storage_unavailable", "message": "Signed download URL could not be created."}) from exc
    return {"download": signed, "file": file_row}

# Auth skeleton. Production should use Supabase Auth or Clerk; this endpoint creates local SaaS records only.
@router.post("/auth/register")
def register(payload: RegisterRequest) -> Dict[str, Any]:
    existing = find_one("users", email=str(payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="User already exists. Use Supabase Auth in production.")
    user = insert("users", {
        "user_id": make_public_id("company").replace("DB-CMP", "DB-USR"),
        "email": str(payload.email),
        "auth_provider": "supabase_auth_expected",
        "status": "pending_auth_provider",
        "role": "customer",
    })
    company = None
    if payload.company_name:
        company = insert("companies", {
            "company_id": make_public_id("company"),
            "company_name": payload.company_name,
            "contact_person": payload.contact_person,
            "email": str(payload.email),
            "subscription_plan": "free",
        })
    log_activity(str(payload.email), "auth.register_skeleton", {"user_id": user["user_id"]})
    return {"user": user, "company": company, "note": "Production auth should be completed through Supabase Auth or Clerk."}

@router.post("/auth/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    user = find_one("users", email=str(payload.email))
    if not user:
        raise HTTPException(status_code=404, detail="User record not found. Connect Supabase Auth for production login.")
    return {"status": "auth_provider_required", "user": user, "note": "Use Supabase Auth token exchange in production."}

@router.post("/auth/logout")
def logout(response: Response) -> Dict[str, str]:
    response.delete_cookie(AUTH_COOKIE, path="/")
    clear_csrf_cookie(response)
    return {"status": "ok", "message": "Client should clear auth session through the auth provider."}

@router.get("/users/profile")
def profile(authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    current = _required_saas_user(authorization, auth_cookie)
    user = find_one("users", email=current.get("email"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user": user}

@router.post("/companies/create")
def create_company(payload: CompanyRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    current = _required_saas_user(authorization, auth_cookie)
    row = payload.model_dump()
    row["owner_email"] = current.get("email")
    row["email"] = row.get("email") or current.get("email")
    company = insert("companies", {**row, "company_id": make_public_id("company"), "subscription_plan": "free"})
    return {"company": company}

@router.post("/companies/update")
def update_company(company_id: str, payload: CompanyRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    current = _required_saas_user(authorization, auth_cookie)
    existing = find_one("companies", company_id=company_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found.")
    if existing.get("owner_email") and existing.get("owner_email") != current.get("email"):
        raise HTTPException(status_code=403, detail="You can update only your own company.")
    company = update_one("companies", "company_id", company_id, payload.model_dump(exclude_unset=True))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return {"company": company}

@router.post("/projects/create")
def create_saas_project(payload: ProjectRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    row = payload.model_dump()
    if production_store_configured():
        auth_user_id = user.get("supabase_user_id") if uuid_like(str(user.get("supabase_user_id") or "")) else None
        profile = None
        if auth_user_id:
            try:
                profile_rows = select_production_rows("users_profile", {"auth_user_id": auth_user_id}, limit=1)
                profile = profile_rows[0] if profile_rows else None
            except ProductionStoreError:
                profile = None
        project_payload = {
            "user_id": str((profile or {}).get("id") or auth_user_id or "") or None,
            "company_id": (profile or {}).get("company_id"),
            "project_name": row.get("project_name"),
            "location": row.get("location"),
            "client_name": row.get("client"),
            "contractor_name": row.get("contractor"),
            "contract_value": row.get("contract_value"),
            "currency": row.get("currency") or "AZN",
            "start_date": row.get("start_date") or None,
            "planned_finish_date": row.get("end_date") or None,
            "current_status": row.get("project_status") or "draft",
            "owner_email": user.get("email"),
        }
        project_payload = {key: value for key, value in project_payload.items() if value not in (None, "")}
        try:
            project = insert_production_row("projects", project_payload)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project could not be created."}) from exc
        return {"project": _project_api_row(project)}
    row["owner_email"] = user.get("email")
    row.setdefault("status", row.get("project_status") or "draft")
    project = insert("projects", {**row, "project_id": make_public_id("project")})
    log_activity(project.get("owner_email"), "project.create", {"project_id": project["project_id"]})
    return {"project": project}

def _project_api_row(project: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(project or {})
    row.setdefault("project_id", str(row.get("id") or ""))
    row.setdefault("project_status", row.get("current_status") or row.get("status") or "draft")
    row.setdefault("client", row.get("client_name"))
    row.setdefault("contractor", row.get("contractor_name"))
    row.setdefault("end_date", row.get("planned_finish_date"))
    return row


def _project_lookup(project_id: str) -> Optional[Dict[str, Any]]:
    if production_store_configured():
        filters = [{"id": project_id}] if uuid_like(project_id) else []
        filters.append({"project_id": project_id})
        for item in filters:
            try:
                rows = select_production_rows("projects", item, limit=1)
            except ProductionStoreError:
                if item.get("project_id") == project_id:
                    continue
                raise
            if rows:
                return _project_api_row(rows[0])
        return None
    return find_one("projects", project_id=project_id)


def _project_db_id(project: Dict[str, Any], requested_project_id: str) -> str:
    return str(project.get("id") or requested_project_id)


def _project_file_rows(project: Dict[str, Any], requested_project_id: str) -> List[Dict[str, Any]]:
    db_project_id = _project_db_id(project, requested_project_id)
    if production_store_configured():
        rows = select_production_rows("uploaded_files", {"project_id": db_project_id}, limit=500)
    else:
        rows = list_rows("uploaded_files", project_id=requested_project_id)
    return [row for row in rows if str(row.get("status") or row.get("upload_status") or "").lower() != "deleted"]


def _project_analysis_rows(project: Dict[str, Any], requested_project_id: str) -> List[Dict[str, Any]]:
    db_project_id = _project_db_id(project, requested_project_id)
    if production_store_configured():
        rows = select_production_rows("analysis_results", {"project_id": db_project_id}, limit=100)
    else:
        rows = list_rows("analysis_results", project_id=requested_project_id)
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows


@router.get("/projects/list")
def list_projects(owner_email: Optional[str] = None, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    effective_owner = user.get("email")
    if production_store_configured():
        try:
            rows = select_production_rows("projects", {"owner_email": effective_owner}, limit=500)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Projects could not be listed."}) from exc
        rows = [_project_api_row(row) for row in rows]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return {"projects": rows}
    return {"projects": list_rows("projects", owner_email=effective_owner)}


@router.get("/projects/{project_id}")
def get_saas_project(project_id: str, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    try:
        project = _project_lookup(project_id)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project could not be loaded."}) from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    try:
        files = _project_file_rows(project, project_id)
        analyses = _project_analysis_rows(project, project_id)
    except ProductionStoreError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project detail could not be loaded."}) from exc
    return {"project": project, "uploaded_files": files, "analysis_results": analyses}


def _project_update_payload(payload: ProjectUpdateRequest) -> Dict[str, Any]:
    row = payload.model_dump(exclude_unset=True)
    mapped = {
        "project_name": row.get("project_name"),
        "location": row.get("location"),
        "client_name": row.get("client"),
        "contractor_name": row.get("contractor"),
        "contract_value": row.get("contract_value"),
        "currency": row.get("currency"),
        "start_date": row.get("start_date") or None,
        "planned_finish_date": row.get("end_date") or None,
        "current_status": row.get("project_status"),
        "analysis_type": row.get("analysis_type"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return {key: value for key, value in mapped.items() if value not in (None, "")}


@router.patch("/projects/{project_id}")
def update_saas_project(project_id: str, payload: ProjectUpdateRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    project = _project_lookup(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    patch = _project_update_payload(payload)
    if production_store_configured():
        try:
            updated = update_production_row("projects", {"id": _project_db_id(project, project_id)}, patch)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project could not be updated."}) from exc
        return {"project": _project_api_row(updated or project)}
    local_patch = payload.model_dump(exclude_unset=True)
    local_patch["updated_at"] = datetime.utcnow().isoformat()
    updated = update_one("projects", "project_id", project_id, local_patch)
    return {"project": updated or project}


@router.delete("/projects/{project_id}")
def delete_saas_project(project_id: str, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    project = _project_lookup(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    patch = {"current_status": "deleted", **soft_delete_schedule(), "updated_at": datetime.utcnow().isoformat()}
    if production_store_configured():
        try:
            updated = update_production_row("projects", {"id": _project_db_id(project, project_id)}, patch)
        except ProductionStoreError as exc:
            raise HTTPException(status_code=503, detail={"error": "database_unavailable", "message": "Project could not be deleted."}) from exc
        return {"status": "deleted", "project": _project_api_row(updated or project)}
    updated = update_one("projects", "project_id", project_id, {"project_status": "deleted", "status": "deleted", **soft_delete_schedule(), "updated_at": datetime.utcnow().isoformat()})
    return {"status": "deleted", "project": updated or project}


@router.post("/guest/start")
def start_guest_project(payload: GuestStartRequest) -> Dict[str, Any]:
    result = create_guest_order(str(payload.email), payload.project_name, safe_guest_ttl_days(payload.result_days))
    log_activity(str(payload.email), "guest.start", {"project_id": result["project"]["project_id"]})
    return result

@router.post("/files/upload")
async def upload_saas_files(project_id: str, files: List[UploadFile] = File(...), authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    project = find_one("projects", project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Create project before upload.")
    _assert_project_owner(project, user)
    uploaded = []
    for f in files:
        # This skeleton records metadata. Existing /api/projects/{id}/upload remains the file parser upload path.
        file_id = make_public_id("file")
        row = insert("uploaded_files", {
            "file_id": file_id,
            "project_id": project_id,
            "original_name": f.filename,
            "content_type": f.content_type,
            "size_bytes": getattr(f, "size", None),
            "owner_email": user.get("email"),
            "storage_provider": "supabase_storage_expected",
            "storage_path": f"projects/{project_id}/{file_id}/{f.filename}",
            "status": "metadata_recorded",
        })
        uploaded.append(row)
    return {"project_id": project_id, "uploaded_files": uploaded}

@router.delete("/files/delete")
def delete_file(file_id: str, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE), delete_object: bool = True) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    current = find_one("uploaded_files", file_id=file_id)
    if not current:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_file_owner(current, user)
    storage_delete_status = "not_requested"
    if delete_object and current.get("storage_path") and current.get("storage_provider") == "supabase_storage":
        try:
            delete_storage_object(current["storage_path"])
            storage_delete_status = "deleted"
        except Exception as exc:
            storage_delete_status = "storage_delete_failed"
    file_row = update_one("uploaded_files", "file_id", file_id, {"status": "deleted", **soft_delete_schedule(), "storage_delete_status": storage_delete_status})
    log_activity(user.get("email") if user else current.get("owner_email"), "file.delete", {"file_id": file_id, "storage_delete_status": storage_delete_status})
    return {"status": "deleted", "file": file_row, "storage_delete_status": storage_delete_status}

@router.get("/files/list")
def list_files(project_id: str, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    project = find_one("projects", project_id=project_id)
    if project:
        _assert_project_owner(project, user)
    return {"uploaded_files": [row for row in list_rows("uploaded_files", project_id=project_id) if row.get("status") != "deleted"]}

@router.post("/analysis/create")
def create_analysis_record(payload: AnalysisCreateRequest, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    project = find_one("projects", project_id=payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _assert_project_owner(project, user)
    owner_email = user.get("email")
    if payload.uploaded_file_ids:
        for file_id in payload.uploaded_file_ids:
            file_row = find_one("uploaded_files", file_id=file_id)
            if not file_row or file_row.get("project_id") != payload.project_id or file_row.get("status") not in {"uploaded", "metadata_recorded", "local_record"}:
                raise HTTPException(status_code=400, detail={"error": "invalid_analysis_file", "message": "One or more files are not uploaded or do not belong to this project.", "file_id": file_id})
            _assert_file_owner(file_row, user)
    credit_check = require_credit(owner_email=owner_email, project_id=payload.project_id)
    if not credit_check.get("allowed"):
        raise HTTPException(status_code=402, detail={
            "message": "No analysis credits available. Complete payment, upgrade plan, or buy an extra project review.",
            "credits": credit_check,
        })
    analysis = insert("analysis_results", {
        "analysis_id": make_public_id("analysis"),
        "project_id": payload.project_id,
        "uploaded_file_ids": payload.uploaded_file_ids,
        "analysis_type": payload.analysis_type,
        "package_name": payload.package_name or payload.analysis_type,
        "owner_email": owner_email,
        "status": "queued",
        "result_json": {},
    })
    credit_usage = None
    if payload.consume_credit_now:
        credit_usage = consume_credit(owner_email=owner_email, project_id=payload.project_id, analysis_id=analysis["analysis_id"])
    log_activity(owner_email, "analysis.create", {"analysis_id": analysis["analysis_id"], "project_id": payload.project_id})
    return {"analysis": analysis, "credit_usage": credit_usage, "note": "Call existing project analyze endpoint to run current parser/dashboard engine."}

@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str, authorization: Optional[str] = Header(default=None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    row = find_one("analysis_results", analysis_id=analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if row.get("owner_email") != user.get("email"):
        raise HTTPException(status_code=403, detail="You can access only your own analysis.")
    return {"analysis": row}

@router.get("/guest-result/{token}")
def guest_result(token: str) -> Dict[str, Any]:
    token = validate_public_token(token, "guest result link")
    order = find_one("guest_orders", result_token=token)
    if not order:
        raise HTTPException(status_code=404, detail="Guest result link not found.")
    if order.get("result_expires_at") and order["result_expires_at"] < datetime.utcnow().isoformat():
        raise HTTPException(status_code=410, detail="Guest result link has expired.")
    project = find_one("projects", guest_order_id=order.get("guest_order_id"))
    analyses = list_rows("analysis_results", project_id=project.get("project_id") if project else None)
    return {"guest_order": order, "project": project, "analysis_results": analyses}

@router.post("/payments/create-one-time-checkout")
def create_one_time_checkout(payload: CheckoutRequest) -> Dict[str, Any]:
    if payload.plan_code != "single":
        raise HTTPException(status_code=400, detail="Use create-subscription-checkout for Plus or Pro.")
    try:
        return create_billing_checkout_session(_checkout_current_user(payload), payload.plan_code, payload.project_id, payload.success_url, payload.cancel_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "checkout_failed", "message": "Checkout could not be created. Please try again."}) from exc

@router.post("/payments/create-subscription-checkout")
def create_subscription_checkout(payload: CheckoutRequest) -> Dict[str, Any]:
    if payload.plan_code not in {"plus", "pro"}:
        raise HTTPException(status_code=400, detail="Subscription checkout supports Plus and Pro only.")
    try:
        return create_billing_checkout_session(_checkout_current_user(payload), payload.plan_code, payload.project_id, payload.success_url, payload.cancel_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "checkout_failed", "message": "Checkout could not be created. Please try again."}) from exc

@router.post("/payments/activate-pilot-checkout")
def activate_pilot_checkout(checkout_id: str, customer_email: Optional[EmailStr] = None) -> Dict[str, Any]:
    """Pilot helper for non-production checkout testing. Disable before production launch."""
    if production_security_enabled() or not bool_env("DEVBAREUN_ENABLE_PILOT_CHECKOUT", False):
        raise HTTPException(status_code=403, detail="Pilot checkout activation is disabled.")
    session = find_one("checkout_sessions", checkout_id=checkout_id)
    if not session:
        raise HTTPException(status_code=404, detail="Pilot checkout session was not found.")
    owner_email = str(customer_email or session.get("customer_email") or f"guest-{checkout_id.lower()}@devbareun.local")
    payment = insert("payments", {
        "payment_id": make_public_id("payment"),
        "checkout_id": checkout_id,
        "owner_email": owner_email,
        "project_id": session.get("project_id"),
        "plan_code": session.get("plan_code") or "single",
        "status": "paid",
        "paid_at": datetime.utcnow().isoformat(),
    })
    update_one("checkout_sessions", "checkout_id", checkout_id, {"status": "paid", "paid_at": datetime.utcnow().isoformat()})
    return {"status": "activated", "payment": payment}

@router.post("/payments/webhook")
async def payment_webhook(request: Request) -> Dict[str, Any]:
    """Compatibility webhook path. Preserve 5xx delivery retry semantics."""
    body = await request.body()
    return handle_billing_webhook(body, request.headers.get("x-signature"), provider_hint="lemonsqueezy")

@router.get("/subscriptions/status")
def subscription_status(authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    return {"subscriptions": list_rows("subscriptions", owner_email=user.get("email"))}

@router.get("/credits/status")
def credits_status(project_id: Optional[str] = None, authorization: Optional[str] = Header(None), auth_cookie: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE)) -> Dict[str, Any]:
    user = _required_saas_user(authorization, auth_cookie)
    return {"credit_summary": credit_summary(owner_email=user.get("email"), project_id=project_id)}

