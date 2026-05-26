from __future__ import annotations

import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .analyzer import build_dashboard, apply_baseline_actual_guardrails
from .parser import ConstructionFileParser
from .reports import build_excel_bytes, build_pdf_bytes
from .openai_mapper import build_workbook_context, run_assisted_mapping, should_call_openai
from .version import APP_VERSION

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "projects"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _allowed_origins() -> List[str]:
    raw = os.getenv("DEVBAREUN_ALLOWED_ORIGINS")
    if raw:
        values = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        return values or ["http://localhost:3000"]
    return [
        "https://devbareun.com",
        "https://www.devbareun.com",
        "https://devbareun.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

app = FastAPI(
    title="DevBareun Construction Analytics Backend",
    version=APP_VERSION,
    description="MVP backend for universal construction file parsing, project dashboard generation and report exports.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
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


def _health_payload() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "devbareun-backend",
        "version": APP_VERSION,
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/")
def root() -> Dict[str, str]:
    return _health_payload()


@app.get("/health")
def health_public() -> Dict[str, str]:
    return _health_payload()


@app.get("/api/health")
def health() -> Dict[str, str]:
    return _health_payload()


@app.post("/api/projects")
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    project_id = uuid4().hex[:12]
    project = {
        "project_id": project_id,
        "project_name": payload.project_name or "DevBareun Uploaded Project",
        "customer_email": payload.customer_email or "info@devbareun.com",
        "analysis_type": payload.analysis_type or "all",
        "paid": False,
        "created_at": datetime.utcnow().isoformat(),
        "files": [],
    }
    _save_project(project_id, project)
    (UPLOAD_DIR / project_id).mkdir(parents=True, exist_ok=True)
    return {"project_id": project_id, "project": project}


@app.post("/api/projects/{project_id}/upload")
async def upload_files(project_id: str, files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    max_files = _int_env("DEVBAREUN_MAX_FILES", 12)
    max_file_bytes = _int_env("DEVBAREUN_MAX_FILE_MB", 30) * 1024 * 1024
    max_total_bytes = _int_env("DEVBAREUN_MAX_TOTAL_MB", 120) * 1024 * 1024
    if len(files) > max_files:
        raise HTTPException(status_code=400, detail=f"Too many files. Maximum allowed: {max_files}.")

    upload_path = UPLOAD_DIR / project_id
    upload_path.mkdir(parents=True, exist_ok=True)
    saved_files = []
    allowed = {".xlsx", ".xlsm", ".xls", ".csv", ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xer", ".xml"}
    total_bytes = 0

    for upload in files:
        original_name = Path(upload.filename or "uploaded_file").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {original_name}")

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
                        raise HTTPException(status_code=413, detail=f"File is too large: {original_name}. Maximum {_int_env('DEVBAREUN_MAX_FILE_MB', 30)}MB per file.")
                    if total_bytes > max_total_bytes:
                        raise HTTPException(status_code=413, detail=f"Upload batch is too large. Maximum {_int_env('DEVBAREUN_MAX_TOTAL_MB', 120)}MB total.")
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


@app.post("/api/payments/create-checkout")
def create_checkout(payload: PaymentRequest) -> Dict[str, Any]:
    project_id = _safe_project_id(payload.project_id)
    project = _load_project(project_id)

    if os.getenv("STRIPE_SECRET_KEY"):
        session = _create_stripe_checkout_session(project_id, payload.success_url, payload.cancel_url)
        project["paid"] = False
        project["payment_status"] = "stripe_checkout_created"
        project["stripe_checkout_session_id"] = session.get("id")
        project["updated_at"] = datetime.utcnow().isoformat()
        _save_project(project_id, project)
        return {
            "project_id": project_id,
            "status": "checkout_required",
            "mode": "stripe",
            "checkout_url": session.get("url"),
            "session_id": session.get("id"),
        }

    if _env_bool("DEVBAREUN_ENABLE_MOCK_PAYMENT", True):
        project["paid"] = True
        project["payment_status"] = "mock_pilot_paid"
        project["updated_at"] = datetime.utcnow().isoformat()
        _save_project(project_id, project)
        return {"project_id": project_id, "status": "paid", "mode": "mock_pilot", "note": "Pilot mode only. Set STRIPE_SECRET_KEY and disable DEVBAREUN_ENABLE_MOCK_PAYMENT before commercial launch."}

    raise HTTPException(status_code=503, detail="Payment provider is not configured. Set STRIPE_SECRET_KEY or enable DEVBAREUN_ENABLE_MOCK_PAYMENT for pilot testing.")


@app.post("/api/projects/{project_id}/preflight")
def preflight_project(project_id: str, payload: AnalysisRequest | None = None) -> Dict[str, Any]:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    paths = _project_upload_paths(project_id, project)
    if not paths:
        raise HTTPException(status_code=400, detail="No uploaded files found for this project.")

    analysis_type = (payload.analysis_type if payload else None) or project.get("analysis_type") or "all"
    parser = ConstructionFileParser(analysis_type=analysis_type)
    parsed = parser.parse_files(paths)
    apply_baseline_actual_guardrails(parsed, analysis_type)
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
        "assisted_mapping": assisted_mapping or {"enabled": False, "reason": "Rule-based confidence was sufficient or OpenAI mapping is disabled."},
        "evidence": {
            "actual_execution_source": parsed.evidence.get("actual_execution_source"),
            "f2_completed_amount": parsed.evidence.get("f2_completed_amount"),
            "az_f2_parser": parsed.evidence.get("az_f2_parser"),
            "assisted_mapping": parsed.evidence.get("assisted_mapping"),
            "workforce_productivity": parsed.evidence.get("workforce_productivity"),
        },
        "message": "Confirm detected mappings before relying on the final report. Assisted mapping may help classify unclear sheets and columns, but Python calculations remain authoritative.",
    }
    project["preflight"] = response
    project["updated_at"] = datetime.utcnow().isoformat()
    _save_project(project_id, project)
    return response


@app.post("/api/projects/{project_id}/analyze")
def analyze_project(project_id: str, payload: AnalysisRequest | None = None) -> Dict[str, Any]:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    paths = _project_upload_paths(project_id, project)
    if not paths:
        raise HTTPException(status_code=400, detail="No uploaded files found for this project.")
    if not project.get("paid"):
        raise HTTPException(status_code=402, detail="Payment is required before dashboard generation. Pilot mode uses /api/payments/create-checkout to unlock analysis.")

    analysis_type = (payload.analysis_type if payload else None) or project.get("analysis_type") or "all"
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
    _save_project(project_id, project)
    return result


@app.get("/api/projects/{project_id}/dashboard")
def get_dashboard(project_id: str) -> Dict[str, Any]:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    return project["analysis"]


@app.get("/api/projects/{project_id}/report/pdf")
def get_pdf_report(project_id: str, lang: str = "en") -> Response:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    if not project.get("paid"):
        raise HTTPException(status_code=402, detail="Payment is required before PDF export.")
    pdf_bytes = build_pdf_bytes(project["analysis"], lang=lang)
    report_id = project["analysis"]["dashboard"]["project"].get("report_id", project_id)
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_id}_DevBareun_Report.pdf"'},
    )


@app.get("/api/projects/{project_id}/report/excel")
def get_excel_report(project_id: str, lang: str = "en") -> Response:
    project_id = _safe_project_id(project_id)
    project = _load_project(project_id)
    if "analysis" not in project:
        raise HTTPException(status_code=404, detail="Dashboard has not been generated yet.")
    if not project.get("paid"):
        raise HTTPException(status_code=402, detail="Payment is required before Excel export.")
    excel_bytes = build_excel_bytes(project["analysis"], lang=lang)
    report_id = project["analysis"]["dashboard"]["project"].get("report_id", project_id)
    return Response(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_id}_DevBareun_Analysis.xlsx"'},
    )



def _missing_fields_for_analysis(analysis_type: str, parsed: Any) -> List[str]:
    analysis_type = (analysis_type or "all").lower()
    required = {
        "cost": ["total_cost", "actual_cost"],
        "progress": ["total_cost", "actual_execution"],
        "schedule": ["planned_execution", "actual_execution", "baseline_finish", "estimated_finish"],
        "workforce": ["workforce_current", "workforce_required"],
        "material": [],
        "risk": [],
        "all": ["total_cost", "actual_execution", "planned_execution", "baseline_finish", "workforce_current"],
    }.get(analysis_type, ["total_cost", "actual_execution"])
    missing: List[str] = []
    for field in required:
        if getattr(parsed, field, None) in (None, ""):
            missing.append(field)
    return missing[:5]


def _preflight_confidence(parsed: Any, analysis_type: str) -> int:
    score = 25
    if parsed.project_name: score += 10
    if parsed.currency: score += 5
    if parsed.sheets:
        score += min(25, int(sum(s.confidence for s in parsed.sheets) / max(1, len(parsed.sheets)) * 0.25))
    if analysis_type in {"cost", "all"} and parsed.total_cost is not None: score += 15
    if analysis_type in {"progress", "all"} and parsed.actual_execution is not None: score += 15
    if analysis_type == "schedule" and (parsed.baseline_finish or parsed.planned_execution is not None): score += 20
    if analysis_type == "workforce" and parsed.workforce_current is not None: score += 20
    if analysis_type == "material" and any(getattr(sheet, "detected_type", "") in {"procurement", "material"} for sheet in parsed.sheets): score += 20
    if analysis_type == "risk" and (parsed.warnings or parsed.sheets): score += 20
    return max(0, min(100, score))


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


def _create_stripe_checkout_session(project_id: str, success_url: str | None, cancel_url: str | None) -> Dict[str, Any]:
    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY is not configured.")

    default_success = os.getenv("FRONTEND_SUCCESS_URL", "https://devbareun.com/result-dashboard.html?payment=success&project_id={project_id}&session_id={CHECKOUT_SESSION_ID}")
    default_cancel = os.getenv("FRONTEND_CANCEL_URL", "https://devbareun.com/?payment=cancelled&project_id={project_id}")
    final_success = (success_url or default_success).replace("{project_id}", project_id)
    final_cancel = (cancel_url or default_cancel).replace("{project_id}", project_id)

    data: Dict[str, Any] = {
        "mode": "payment",
        "success_url": final_success,
        "cancel_url": final_cancel,
        "client_reference_id": project_id,
        "metadata[project_id]": project_id,
    }
    price_id = os.getenv("STRIPE_PRICE_ID")
    if price_id:
        data["line_items[0][price]"] = price_id
        data["line_items[0][quantity]"] = "1"
    else:
        data.update({
            "line_items[0][price_data][currency]": os.getenv("DEVBAREUN_STRIPE_CURRENCY", "usd"),
            "line_items[0][price_data][product_data][name]": "DevBareun Project Dashboard",
            "line_items[0][price_data][unit_amount]": str(_int_env("DEVBAREUN_STRIPE_AMOUNT_CENTS", 4900)),
            "line_items[0][quantity]": "1",
        })

    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=encoded,
        method="POST",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"DevBareun/{APP_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Stripe checkout creation failed: {raw}") from exc


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


def _project_upload_paths(project_id: str, project: Dict[str, Any]) -> List[Path]:
    upload_path = UPLOAD_DIR / _safe_project_id(project_id)
    result = []
    for item in project.get("files", []):
        path = upload_path / item.get("stored_name", "")
        if path.exists():
            result.append(path)
    return result
