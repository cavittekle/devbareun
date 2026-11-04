"""Retired pre-SaaS project routes.

The original single-file workflow (project token, local upload, synchronous
analyze, token-protected PDF/Excel) was replaced by authenticated projects,
signed uploads, analysis jobs and report snapshots. The paths stay registered so
old clients receive a clear ``410 Gone`` instead of ``404``. They are hidden
from the OpenAPI schema.
"""
from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["retired project routes"], include_in_schema=False)

RETIRED_DETAIL = {
    "error": "legacy_route_disabled",
    "message": "This legacy project route is retired. Use authenticated project, signed upload, analysis job and delay-analysis report routes.",
}


def _gone() -> NoReturn:
    raise HTTPException(status_code=410, detail=RETIRED_DETAIL)


@router.post("/api/projects")
def create_project() -> None:
    _gone()


@router.post("/api/projects/{project_id}/upload")
def upload_files(project_id: str) -> None:
    _gone()


@router.post("/api/projects/{project_id}/preflight")
def preflight(project_id: str) -> None:
    _gone()


@router.post("/api/projects/{project_id}/analyze")
def analyze(project_id: str) -> None:
    _gone()


@router.get("/api/projects/{project_id}/dashboard")
def get_dashboard(project_id: str) -> None:
    _gone()


@router.get("/api/projects/{project_id}/report/pdf")
def get_pdf_report(project_id: str) -> None:
    _gone()


@router.get("/api/projects/{project_id}/report/excel")
def get_excel_report(project_id: str) -> None:
    _gone()


@router.post("/api/payments/create-checkout")
def create_checkout() -> None:
    _gone()
