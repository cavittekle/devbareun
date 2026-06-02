from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .auth_dependencies import CurrentUser, get_current_user
from .services.billing_service import (
    create_checkout_session,
    create_one_time_checkout,
    create_subscription_checkout,
    get_billing_status,
    get_usage,
    handle_webhook,
)


router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = Field(default="single", max_length=40)
    project_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.post("/create-checkout-session")
async def create_checkout(payload: CheckoutRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return create_checkout_session(current_user, payload.plan, payload.project_id, payload.success_url, payload.cancel_url)


@router.post("/create-subscription-checkout")
async def subscription_checkout(payload: CheckoutRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return create_subscription_checkout(current_user, payload.plan, payload.success_url, payload.cancel_url)


@router.post("/create-one-time-checkout")
async def one_time_checkout(payload: CheckoutRequest, current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return create_one_time_checkout(current_user, payload.project_id, payload.success_url, payload.cancel_url)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> Dict[str, Any]:
    body = await request.body()
    signature = request.headers.get("stripe-signature")
    return handle_webhook(body, signature)


@router.get("/status")
async def billing_status(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return {"billing": get_billing_status(current_user)}


@router.get("/usage")
async def billing_usage(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return {"usage": get_usage(current_user)}

