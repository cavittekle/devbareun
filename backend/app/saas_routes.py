from __future__ import annotations

from fastapi import APIRouter

from .saas_common import _can_access  # Backward-compatible import for release/security tests.
from .saas_admin_routes import router as admin_router
from .saas_public_routes import router as public_router
from .saas_super_admin_routes import router as super_admin_router

router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)
router.include_router(super_admin_router)

__all__ = ["router", "_can_access"]
