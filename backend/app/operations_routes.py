from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from .auth_dependencies import CurrentUser, get_current_user, require_staff_permission
from .services.operations_health_service import operations_health_status

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/health")
async def get_operations_health(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Cross-service operational health for owner/operator staff only."""
    require_staff_permission(current_user, "operations")
    return {"operations_health": operations_health_status()}
