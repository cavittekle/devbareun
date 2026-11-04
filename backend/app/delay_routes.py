"""HTTP API for construction execution and delay analysis.

Public (no login):
* GET  /api/delay-analysis/template          Excel input template
* GET  /api/delay-analysis/sample            example analysis result (JSON)
* GET  /api/delay-analysis/sample/report     example execution report (?format=pdf|xlsx&lang=az|en)

Signed in:
* POST /api/delay-analysis/preview           analyse uploaded files without saving them
* GET  /api/delay-analysis/project/{id}      latest saved delay analysis of a project
* GET  /api/delay-analysis/project/{id}/report  execution report of that analysis
"""
from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from .auth_dependencies import CurrentUser, get_current_user, require_project_owner
from .delay import analyze, run_delay_analysis
from .delay.report import build_delay_excel, build_delay_pdf
from .delay.report_a3 import report_filename
from .delay.sample import TEMPLATE_FILENAME, build_template_bytes
from .delay.sample_estate import estate_sample_input
from .file_validation import validate_magic_signature, validate_upload_metadata
from .services.analysis_job_service import get_latest_analysis_result
from .upload_security import UploadSecurityScreeningError, screen_materialized_upload

router = APIRouter(prefix="/api/delay-analysis", tags=["delay-analysis"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
READABLE_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".csv", ".xer", ".xml"}
MAX_PREVIEW_FILES = 5
MAX_PREVIEW_BYTES = 15 * 1024 * 1024


def _report_response(result: Dict[str, Any], report_format: str, lang: str, stem: str) -> Response:
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=(result.get("error") or {}).get("en") or "Delay analysis is not available.")
    fmt = "xlsx" if report_format.lower() in {"xlsx", "excel", "xls"} else "pdf"
    lang = "az" if lang.lower().startswith("az") else "en"
    if fmt == "xlsx":
        content, media = build_delay_excel(result, lang), XLSX
    else:
        content, media = build_delay_pdf(result, lang), "application/pdf"
    filename = f"{stem}-{lang}.{fmt}"
    disposition = f'attachment; filename="{filename}"'
    if (result.get("executive") or {}).get("ok"):
        # "<Project> icra hesabatı -10.2026.pdf"; the ASCII name stays as a fallback.
        readable = report_filename(result, lang)[:-4] + f".{fmt}"
        disposition += f"; filename*=UTF-8''{quote(readable)}"
    return Response(content, media_type=media, headers={"Content-Disposition": disposition})


@lru_cache(maxsize=1)
def _sample_result() -> Dict[str, Any]:
    result = analyze(estate_sample_input())
    result["is_example"] = True
    return result


@router.get("/template")
def download_template() -> Response:
    return Response(build_template_bytes(), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{TEMPLATE_FILENAME}"'})


@router.get("/sample")
def sample_analysis() -> Dict[str, Any]:
    return _sample_result()


@router.get("/sample/report")
def sample_report(format: str = Query(default="pdf", max_length=8), lang: str = Query(default="az", max_length=5)) -> Response:
    return _report_response(_sample_result(), format, lang, "devbareun-example-delay-report")


@router.post("/preview")
def preview_analysis(
    files: List[UploadFile] = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Choose at least one schedule or progress file.")
    if len(files) > MAX_PREVIEW_FILES:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_PREVIEW_FILES} files can be analysed at once.")
    with tempfile.TemporaryDirectory(prefix="devbareun_delay_") as temp:
        paths: List[Path] = []
        for index, upload in enumerate(files):
            # Sync route: FastAPI runs it in a worker thread, so parsing large
            # workbooks never blocks the event loop.
            content = upload.file.read(MAX_PREVIEW_BYTES + 1)
            try:
                meta = validate_upload_metadata(upload.filename or "", upload.content_type, len(content), MAX_PREVIEW_BYTES)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            suffix = Path(meta["original_filename"]).suffix.lower()
            if suffix not in READABLE_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Delay analysis reads Excel, CSV, Primavera XER or MS Project XML files.")
            if not validate_magic_signature(content[:4096], meta["original_filename"]):
                raise HTTPException(status_code=400, detail="File content does not match its extension.")
            path = Path(temp) / f"{index}-{meta['original_filename']}"
            path.write_bytes(content)
            try:
                screen_materialized_upload({"original_filename": meta["original_filename"]}, path)
            except UploadSecurityScreeningError as exc:
                raise HTTPException(status_code=400, detail=f"File was blocked by security screening ({exc.code}).") from exc
            paths.append(path)
        return run_delay_analysis(paths)


async def _project_delay_result(project_id: str, current_user: CurrentUser) -> Dict[str, Any]:
    project = await require_project_owner(project_id, current_user, section="projects")
    row = get_latest_analysis_result(project_id, project, current_user)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "analysis_not_ready", "message": "No analysis has been completed for this project yet."})
    dashboard = row.get("dashboard_data") or {}
    result = dashboard.get("delay_analysis")
    if not result:
        raise HTTPException(status_code=404, detail={"error": "legacy_analysis_result", "message": "This analysis was created before delay analysis was available. Run the analysis again."})
    return result


@router.get("/project/{project_id}")
async def project_delay_analysis(project_id: str, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return await _project_delay_result(project_id, current_user)


@router.get("/project/{project_id}/report")
async def project_delay_report(
    project_id: str,
    format: str = Query(default="pdf", max_length=8),
    lang: str = Query(default="az", max_length=5),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    result = await _project_delay_result(project_id, current_user)
    return _report_response(result, format, lang, "devbareun-delay-report")
