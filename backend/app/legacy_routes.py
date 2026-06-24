from __future__ import annotations

import json
import os
import re
import secrets
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from .analyzer import build_dashboard, apply_baseline_actual_guardrails
from .analysis_types import PREMIUM_ANALYSIS_TYPE, normalize_analysis_type, parser_analysis_type
from .auth_dependencies import CurrentUser
from .auth_runtime import AuthError, consume_pilot_credit, get_bearer_token, verify_supabase_token
from .file_validation import validate_upload_metadata
from .openai_mapper import build_workbook_context, run_assisted_mapping, should_call_openai
from .parser import ConstructionFileParser
from .persistence_runtime import save_analysis
from .reports import build_excel_bytes, build_pdf_bytes
from .security_runtime import bool_env, production_security_enabled
from .services.billing_service import create_one_time_checkout as create_billing_one_time_checkout
from .services.premium_analysis import file_group_status
from .supabase_client import is_configured as supabase_is_configured
from .template_manifest import TEMPLATE_MANIFEST

router = APIRouter(
    tags=["legacy project routes"],
    include_in_schema=bool_env("DEVBAREUN_EXPOSE_LEGACY_PROJECT_ROUTES", False),
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "projects"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _require_persistent_project_storage() -> None:
    if production_security_enabled() and not bool_env("DEVBAREUN_ALLOW_EPHEMERAL_PROJECT_UPLOAD", False):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "persistent_storage_required",
                "message": "Production uploads require Supabase Storage. Configure the authenticated storage upload flow before using local project upload endpoints.",
            },
        )

def _require_legacy_project_routes_allowed() -> None:
    if not bool_env("DEVBAREUN_ALLOW_LEGACY_PROJECT_ROUTES", False):
        raise HTTPException(
            status_code=410,
            detail={
                "error": "legacy_route_disabled",
                "message": "This legacy project route is retired. Use authenticated project, signed upload, analysis job and billing routes.",
            },
        )

class ProjectCreate(BaseModel):
    project_name: str | None = Field(default=None, max_length=180)
    customer_email: str | None = None
    analysis_type: str | None = Field(default="all", max_length=40)

class AnalysisRequest(BaseModel):
    analysis_type: str | None = Field(default=None, max_length=40)
    manual_inputs: Dict[str, Any] | None = None

class PaymentRequest(BaseModel):
    project_id: str
    success_url: str | None = None
    cancel_url: str | None = None

@router.post("/api/projects")
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    _require_persistent_project_storage()
    project_id = uuid4().hex[:12]
    project_token = _generate_project_token()
    analysis_type = normalize_analysis_type(payload.analysis_type)
    project = {
        "project_id": project_id,
        "project_name": payload.project_name or "DevBareun Uploaded Project",
        "customer_email": payload.customer_email or "info@devbareun.com",
        "analysis_type": analysis_type,
        "paid": False,
        "project_token": project_token,
        "created_at": datetime.utcnow().isoformat(),
        "files": [],
    }
    _save_project(project_id, project)
    (UPLOAD_DIR / project_id).mkdir(parents=True, exist_ok=True)
    return {"project_id": project_id, "project_token": project_token, "project": _public_project(project)}

@router.post("/api/projects/{project_id}/upload")
async def upload_files(project_id: str, files: List[UploadFile] = File(...), x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    _require_persistent_project_storage()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token)
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    max_files = _int_env("DEVBAREUN_MAX_FILES", 12)
    max_file_bytes = _int_env("DEVBAREUN_MAX_FILE_MB", 30) * 1024 * 1024
    max_total_bytes = _int_env("DEVBAREUN_MAX_TOTAL_MB", 120) * 1024 * 1024
    if len(files) > max_files:
        raise HTTPException(status_code=400, detail={"error": "too_many_files", "message": f"Too many files. Maximum allowed: {max_files}.", "max_files": max_files})

    upload_path = UPLOAD_DIR / project_id
    upload_path.mkdir(parents=True, exist_ok=True)
    saved_files = []
    total_bytes = 0

    for upload in files:
        try:
            meta = validate_upload_metadata(
                upload.filename or "uploaded_file",
                upload.content_type,
                getattr(upload, "size", None),
                max_file_bytes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"error": "invalid_upload", "message": "File metadata is invalid or exceeds the allowed upload limits."}) from exc
        original_name = meta["original_filename"]

        safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:6]}_{_safe_filename(original_name)}"
        target = upload_path / safe_name
        file_bytes = 0
        try:
            with target.open("wb") as f:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    file_bytes += len(chunk)
                    total_bytes += len(chunk)
                    if file_bytes > max_file_bytes:
                        raise HTTPException(status_code=413, detail={"error": "file_too_large", "message": f"File is too large: {original_name}. Maximum {_int_env('DEVBAREUN_MAX_FILE_MB', 30)}MB per file."})
                    if total_bytes > max_total_bytes:
                        raise HTTPException(status_code=413, detail={"error": "upload_batch_too_large", "message": f"Upload batch is too large. Maximum {_int_env('DEVBAREUN_MAX_TOTAL_MB', 120)}MB total."})
                    f.write(chunk)
        except Exception:
            if target.exists():
                target.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        saved_files.append({"original_name": original_name, "stored_name": safe_name, "size": target.stat().st_size})

    project.setdefault("files", []).extend(saved_files)
    project["updated_at"] = datetime.utcnow().isoformat()
    _save_project(project_id, project)
    return {"project_id": project_id, "uploaded": saved_files, "file_count": len(project.get("files", []))}

@router.post("/api/payments/create-checkout")
def create_checkout(payload: PaymentRequest, x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(payload.project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token)

    email = str(project.get("customer_email") or project.get("owner_email") or "").strip().lower()
    if email and "@" in email:
        session = create_billing_one_time_checkout(CurrentUser(id="", auth_user_id="", email=email, plan="single"), project_id, payload.success_url, payload.cancel_url)
        project["paid"] = False
        project["payment_status"] = "checkout_created"
        project["checkout_session_id"] = session.get("session_id")
        project["updated_at"] = datetime.utcnow().isoformat()
        _save_project(project_id, project)
        return {
            "project_id": project_id,
            "status": "checkout_required",
            "mode": session.get("provider") or "lemonsqueezy",
            "checkout_url": session.get("checkout_url"),
            "session_id": session.get("session_id"),
        }

    raise HTTPException(status_code=400, detail="Customer email is required before opening payment provider checkout.")

@router.post("/api/projects/{project_id}/preflight")
def preflight_project(project_id: str, payload: AnalysisRequest | None = None, x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token)
    paths = _project_upload_paths(project_id, project)
    if not paths:
        raise HTTPException(status_code=400, detail="No uploaded files found for this project.")

    analysis_type = normalize_analysis_type((payload.analysis_type if payload else None) or project.get("analysis_type") or "all")
    parser_type = parser_analysis_type(analysis_type)
    parser = ConstructionFileParser(analysis_type=analysis_type)
    parsed = parser.parse_files(paths)
    apply_baseline_actual_guardrails(parsed, parser_type)
    missing = _missing_fields_for_analysis(analysis_type, parsed)
    confidence = _preflight_confidence(parsed, analysis_type)
    sheet_profiles = [s.to_dict() for s in parsed.sheets]
    assisted_mapping = None
    if should_call_openai(confidence):
        mapping_context = build_workbook_context(paths, sheet_profiles, analysis_type)
        assisted_mapping = run_assisted_mapping(mapping_context)
        if assisted_mapping and assisted_mapping.get("enabled"):
            parsed.evidence["assisted_mapping"] = assisted_mapping
            missing = list(dict.fromkeys(missing + assisted_mapping.get("missing_fields", [])))[:8]
            if assisted_mapping.get("warnings"):
                parsed.warnings.extend([f"Assisted mapping: {w}" for w in assisted_mapping.get("warnings", [])])

    response = {
        "project_id": project_id,
        "analysis_type": analysis_type,
        "project_name": parsed.project_name or project.get("project_name"),
        "currency": parsed.currency,
        "confidence": confidence,
        "sheet_profiles": sheet_profiles,
        "file_group_status": _file_group_status_from_parsed(parsed),
        "missing_fields": missing,
        "detected_kpis": {
            "total_cost": parsed.total_cost,
            "planned_cost": parsed.planned_cost,
            "actual_cost": parsed.actual_cost,
            "planned_execution": parsed.planned_execution,
            "actual_execution": parsed.actual_execution,
            "baseline_finish": parsed.baseline_finish,
            "estimated_finish": parsed.estimated_finish,
            "workforce_current": parsed.workforce_current,
            "workforce_required": parsed.workforce_required,
            "workforce_productivity": (parsed.evidence.get("workforce_productivity") or {}).get("summary"),
        },
        "warnings": parsed.warnings,
        "mapping_wizard": _mapping_wizard_for_preflight(parsed, analysis_type, confidence, missing),
        "template_manifest": TEMPLATE_MANIFEST.get(analysis_type, TEMPLATE_MANIFEST[PREMIUM_ANALYSIS_TYPE]),
        "assisted_mapping": assisted_mapping or {"enabled": False, "reason": "Rule-based confidence was sufficient or assisted mapping is disabled."},
        "evidence": {
            "actual_execution_source": parsed.evidence.get("actual_execution_source"),
            "f2_completed_amount": parsed.evidence.get("f2_completed_amount"),
            "az_f2_parser": parsed.evidence.get("az_f2_parser"),
            "assisted_mapping": parsed.evidence.get("assisted_mapping"),
            "workforce_productivity": parsed.evidence.get("workforce_productivity"),
        },
        "message": "Confirm detected mappings before relying on the final report. Assisted mapping may help classify unclear sheets and columns, but calculations remain authoritative.",
    }
    project["preflight"] = response
    project["updated_at"] = datetime.utcnow().isoformat()
    _save_project(project_id, project)
    return response

@router.post("/api/projects/{project_id}/analyze")
async def analyze_project(project_id: str, payload: AnalysisRequest | None = None, authorization: str | None = Header(None), x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token)
    paths = _project_upload_paths(project_id, project)
    if not paths:
        raise HTTPException(status_code=400, detail="No uploaded files found for this project.")

    access = await _ensure_analysis_access(project, authorization)

    analysis_type = normalize_analysis_type((payload.analysis_type if payload else None) or project.get("analysis_type") or "all")
    parser = ConstructionFileParser(analysis_type=analysis_type)
    parsed = parser.parse_files(paths)
    _apply_manual_inputs(parsed, payload.manual_inputs if payload else None)
    if not parsed.project_name or parsed.project_name == "DevBareun Uploaded Project":
        parsed.project_name = project.get("project_name") or parsed.project_name

    result = build_dashboard(project_id, parsed, analysis_type=analysis_type)
    project["analysis_type"] = analysis_type
    project["project_name"] = result["dashboard"]["project"]["name"]
    project["analysis"] = result
    project["analyzed_at"] = datetime.utcnow().isoformat()
    project["analysis_access_mode"] = access.get("mode")

    user = access.get("user")
    saved_analysis = None
    if user:
        saved_analysis = await save_analysis(user.email, {
            "project_id": project_id,
            "project_name": project.get("project_name"),
            "analysis_type": analysis_type,
            "dashboard": result.get("dashboard", {}),
            "kpis": result.get("dashboard", {}).get("kpis", {}),
            "report_payload": result,
            "status": "completed",
            "language": "en",
            "print_size": "A4",
        })
        result.setdefault("workspace", {})["saved_analysis_id"] = saved_analysis.get("analysis_id")
        result["workspace"]["report_id"] = saved_analysis.get("report_id")
        result["workspace"]["credits_remaining"] = (access.get("usage") or {}).get("credits_remaining")

    project["workspace_analysis_id"] = saved_analysis.get("analysis_id") if saved_analysis else project.get("workspace_analysis_id")
    project["workspace_report_id"] = saved_analysis.get("report_id") if saved_analysis else project.get("workspace_report_id")
    project["updated_at"] = datetime.utcnow().isoformat()
    _save_project(project_id, project)
    return result

@router.get("/api/projects/{project_id}/dashboard")
def get_dashboard(project_id: str, project_token: str | None = None, x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Dict[str, Any]:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token or project_token)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    return project["analysis"]

@router.get("/api/projects/{project_id}/report/pdf")
async def get_pdf_report(project_id: str, lang: str = "en", paper: str = "a4", project_token: str | None = None, authorization: str | None = Header(None), x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Response:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token or project_token)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    await _ensure_export_access(project, authorization, "PDF")
    pdf_bytes = build_pdf_bytes(project["analysis"], lang=lang, paper=paper)
    report_id = project["analysis"]["dashboard"]["project"].get("report_id", project_id)
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_id}_DevBareun_Report_{str(paper).upper()}.pdf"'},
    )

@router.get("/api/projects/{project_id}/report/excel")
async def get_excel_report(project_id: str, lang: str = "en", project_token: str | None = None, authorization: str | None = Header(None), x_project_token: str | None = Header(None, alias="X-Project-Token")) -> Response:
    _require_legacy_project_routes_allowed()
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    _require_project_token(project, x_project_token or project_token)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    await _ensure_export_access(project, authorization, "Excel")
    excel_bytes = build_excel_bytes(project["analysis"], lang=lang)
    report_id = project["analysis"]["dashboard"]["project"].get("report_id", project_id)
    return Response(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_id}_DevBareun_Analysis.xlsx"'},
    )

async def _optional_workspace_user(authorization: str | None):
    token = get_bearer_token(authorization)
    if not token:
        return None, None
    try:
        return await verify_supabase_token(token), token
    except AuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or expired session."}) from exc

async def _ensure_analysis_access(project: Dict[str, Any], authorization: str | None) -> Dict[str, Any]:
    """Allow analysis when the legacy project is paid or the workspace has credits."""
    if project.get("paid"):
        return {"allowed": True, "mode": "paid_project", "user": None, "token": None}
    user, token = await _optional_workspace_user(authorization)
    if user:
        try:
            usage = consume_pilot_credit(token)
        except AuthError as exc:
            raise HTTPException(status_code=402, detail={"error": "credit_required", "message": "A valid workspace credit is required before dashboard generation."}) from exc
        project["workspace_owner_email"] = user.email
        project["workspace_plan"] = user.plan
        project["workspace_payment_status"] = "credit_unlocked"
        return {"allowed": True, "mode": "workspace_credit", "user": user, "token": token, "usage": usage}
    raise HTTPException(status_code=402, detail="Payment or workspace credit is required before dashboard generation.")

async def _ensure_export_access(project: Dict[str, Any], authorization: str | None, export_name: str) -> Dict[str, Any]:
    if project.get("paid"):
        return {"allowed": True, "mode": "paid_project"}
    user, token = await _optional_workspace_user(authorization)
    if user and project.get("workspace_owner_email") == user.email:
        return {"allowed": True, "mode": "workspace_owner", "user": user, "token": token}
    raise HTTPException(status_code=402, detail={"error": "payment_or_workspace_required", "message": f"Payment or workspace ownership is required before {export_name} export."})

def _mapping_wizard_for_preflight(parsed: Any, analysis_type: str, confidence: int, missing: List[str]) -> Dict[str, Any]:
    analysis_type = normalize_analysis_type(analysis_type)
    profiles = [s.to_dict() for s in parsed.sheets]
    strong = [p for p in profiles if int(p.get("confidence") or 0) >= 75]
    weak = [p for p in profiles if int(p.get("confidence") or 0) < 60]
    field_sources: Dict[str, Any] = {}
    for p in profiles:
        for canonical, column_name in (p.get("mapped_columns") or {}).items():
            field_sources.setdefault(canonical, []).append({
                "file": p.get("file_name"),
                "sheet": p.get("sheet_name"),
                "column": column_name,
                "detected_type": p.get("detected_type"),
                "confidence": p.get("confidence"),
            })
    required = _required_fields_for_mapping(analysis_type)
    def has_confirmed_value(field: str) -> bool:
        if hasattr(parsed, field):
            value = getattr(parsed, field, None)
            return value not in (None, "")
        # For higher-level package requirements such as material_stock or risk_register,
        # there may be no direct ParsedProjectData attribute. In those cases, a mapped
        # source is still useful as evidence for the wizard.
        return field in field_sources

    detected_required = [field for field in required if has_confirmed_value(field)]
    mapped_required = [field for field in required if field in field_sources]
    missing_required = [field for field in required if field not in detected_required]
    readiness = max(0, min(100, int(confidence * 0.65 + (len(detected_required) / max(1, len(required))) * 35)))
    return {
        "readiness_score": readiness,
        "template": TEMPLATE_MANIFEST.get(analysis_type, TEMPLATE_MANIFEST[PREMIUM_ANALYSIS_TYPE]),
        "required_fields": required,
        "detected_required_fields": detected_required,
        "mapped_required_fields": mapped_required,
        "missing_required_fields": list(dict.fromkeys(missing_required + list(missing or [])))[:10],
        "field_sources": field_sources,
        "sheet_summary": {
            "total": len(profiles),
            "strong": len(strong),
            "weak": len(weak),
            "strong_sheets": strong[:6],
            "weak_sheets": weak[:6],
        },
        "instructions": [
            "Review detected sheets and mapped columns before generating the dashboard.",
            "Fill missing fields manually only if they are confirmed from project documents.",
            "Download the package-specific template when source files do not have clear headers.",
        ],
    }

def _required_fields_for_mapping(analysis_type: str) -> List[str]:
    analysis_type = normalize_analysis_type(analysis_type)
    return {
        "cost": ["total_cost", "actual_cost"],
        "schedule": ["planned_execution", "actual_execution", "baseline_finish", "estimated_finish", "workforce_current", "workforce_required"],
        "material": ["material_stock", "delivery_status", "daily_consumption"],
        "risk": ["risk_register", "decision_required", "owner", "deadline"],
        PREMIUM_ANALYSIS_TYPE: ["total_cost", "actual_cost", "planned_execution", "actual_execution", "workforce_current", "material_stock", "risk_register"],
    }.get(analysis_type, ["total_cost", "actual_execution"])

def _missing_fields_for_analysis(analysis_type: str, parsed: Any) -> List[str]:
    analysis_type = normalize_analysis_type(analysis_type)
    required = {
        "cost": ["total_cost", "actual_cost"],
        "progress": ["total_cost", "actual_execution"],
        "schedule": ["planned_execution", "actual_execution", "baseline_finish", "estimated_finish"],
        "workforce": ["workforce_current", "workforce_required"],
        "material": [],
        "risk": [],
        PREMIUM_ANALYSIS_TYPE: ["total_cost", "actual_execution", "planned_execution", "baseline_finish", "workforce_current"],
    }.get(analysis_type, ["total_cost", "actual_execution"])
    missing: List[str] = []
    for field in required:
        if getattr(parsed, field, None) in (None, ""):
            missing.append(field)
    return missing[:5]

def _preflight_confidence(parsed: Any, analysis_type: str) -> int:
    analysis_type = normalize_analysis_type(analysis_type)
    parser_type = parser_analysis_type(analysis_type)
    score = 25
    if parsed.project_name: score += 10
    if parsed.currency: score += 5
    if parsed.sheets:
        score += min(25, int(sum(s.confidence for s in parsed.sheets) / max(1, len(parsed.sheets)) * 0.25))
    if parser_type in {"cost", "all"} and parsed.total_cost is not None: score += 15
    if parser_type in {"progress", "all"} and parsed.actual_execution is not None: score += 15
    if parser_type in {"schedule", "all"} and (parsed.baseline_finish or parsed.planned_execution is not None): score += 20
    if parser_type in {"workforce", "all"} and parsed.workforce_current is not None: score += 20
    if parser_type in {"material", "all"} and any(getattr(sheet, "detected_type", "") in {"procurement", "material"} for sheet in parsed.sheets): score += 20
    if parser_type in {"risk", "all"} and (parsed.warnings or parsed.sheets): score += 20
    return max(0, min(100, score))

def _file_group_status_from_parsed(parsed: Any) -> Dict[str, Any]:
    normalized = {
        "project_info": {"currency": parsed.currency or "USD"},
        "cost_data": [
            {"name": "total_budget", "value": parsed.total_cost},
            {"name": "actual_cost", "value": parsed.actual_cost},
        ],
        "schedule_data": [{"baseline_finish": parsed.baseline_finish, "forecast_finish": parsed.estimated_finish, "delay_days": parsed.delay_days}],
        "progress_data": [
            {"name": "planned_progress_percent", "value": parsed.planned_execution},
            {"name": "actual_progress_percent", "value": parsed.actual_execution},
        ],
        "manpower_data": [
            {"name": "current_workforce", "value": parsed.workforce_current},
            {"name": "required_workforce", "value": parsed.workforce_required},
        ],
        "material_data": [{"detected_material_sources": len([s for s in parsed.sheets if s.detected_type in {"material", "procurement"}])}],
        "risk_signals": [{"category": "Data quality risk", "value": w} for w in parsed.warnings],
        "evidence": {"sheet_profiles": [s.to_dict() for s in parsed.sheets]},
        "warnings": parsed.warnings,
    }
    return file_group_status(normalized)

def _apply_manual_inputs(parsed: Any, manual_inputs: Dict[str, Any] | None) -> None:
    if not manual_inputs:
        return
    numeric_fields = {"planned_execution", "actual_execution", "total_cost", "actual_cost", "planned_cost", "workforce_current", "workforce_required"}
    date_fields = {"baseline_finish", "estimated_finish"}
    for key, value in manual_inputs.items():
        if not hasattr(parsed, key) or value in (None, ""):
            continue
        try:
            if key in numeric_fields:
                setattr(parsed, key, _parse_manual_number(value))
            elif key in date_fields:
                setattr(parsed, key, str(value))
        except Exception:
            parsed.warnings.append(f"Manual input for {key} could not be applied.")

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _safe_project_id(project_id: str) -> str:
    value = str(project_id or "").strip()
    if not re.fullmatch(r"[a-f0-9]{12}", value):
        raise HTTPException(status_code=400, detail="Invalid project id.")
    return value

def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._() -]+", "_", Path(name).name).strip(" .")
    return cleaned[:140] or "uploaded_file"

def _parse_manual_number(value: Any) -> float:
    text = str(value).strip().replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = text.replace(",", ".") if len(parts[-1]) in {1, 2} else text.replace(",", "")
    return float(text)

def _project_file(project_id: str) -> Path:
    return DATA_DIR / f"{_safe_project_id(project_id)}.json"

def _save_project(project_id: str, data: Dict[str, Any]) -> None:
    with _project_file(project_id).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_project(project_id: str) -> Dict[str, Any]:
    path = _project_file(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found.")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _public_project(project: Dict[str, Any]) -> Dict[str, Any]:
    clean = dict(project)
    clean.pop("project_token", None)
    return clean

def _generate_project_token() -> str:
    return "dbr_proj_" + secrets.token_urlsafe(32)

def _require_project_token(project: Dict[str, Any], provided_token: str | None) -> None:
    expected = str(project.get("project_token") or "")
    if not expected:
        raise HTTPException(status_code=500, detail="Project token missing on server record.")
    token = (provided_token or "").strip()
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Valid project token is required.")

def _safe_checkout_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Checkout redirect URL must be http/https.")
    allowed = [item.strip().rstrip("/") for item in os.getenv("DEVBAREUN_CHECKOUT_ALLOWED_ORIGINS", "").split(",") if item.strip()]
    if not allowed:
        allowed = [
            "https://devbareun.com",
            "https://www.devbareun.com",
            "https://devbareun.vercel.app",
        ]
        if not production_security_enabled():
            allowed.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ])
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin not in allowed:
        raise HTTPException(status_code=400, detail="Checkout redirect origin is not allowed.")
    return url

def _project_upload_paths(project_id: str, project: Dict[str, Any]) -> List[Path]:
    upload_path = UPLOAD_DIR / _safe_project_id(project_id)
    result = []
    for item in project.get("files", []):
        path = upload_path / item.get("stored_name", "")
        if path.exists():
            result.append(path)
    return result
