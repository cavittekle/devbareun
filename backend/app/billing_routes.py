from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    plan_code: Optional[str] = Field(default=None, max_length=40)
    project_id: Optional[str] = None
    customer_email: Optional[str] = Field(default=None, max_length=320)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


async def get_optional_current_user(authorization: Optional[str] = Header(default=None)) -> Optional[CurrentUser]:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise


def _checkout_plan(payload: CheckoutRequest) -> str:
    return str(payload.plan_code or payload.plan or "single").strip().lower()


def _checkout_user(payload: CheckoutRequest, current_user: Optional[CurrentUser]) -> CurrentUser:
    if current_user:
        return current_user
    email = str(payload.customer_email or "").strip().lower()
    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail={"error": "customer_email_required", "message": "Customer email is required for guest checkout."},
        )
    return CurrentUser(id="", auth_user_id="", email=email, plan=_checkout_plan(payload))


@router.post("/create-checkout-session")
async def create_checkout(payload: CheckoutRequest, current_user: Optional[CurrentUser] = Depends(get_optional_current_user)) -> Dict[str, Any]:
    return create_checkout_session(_checkout_user(payload, current_user), _checkout_plan(payload), payload.project_id, payload.success_url, payload.cancel_url)


@router.post("/create-subscription-checkout")
async def subscription_checkout(payload: CheckoutRequest, current_user: Optional[CurrentUser] = Depends(get_optional_current_user)) -> Dict[str, Any]:
    return create_subscription_checkout(_checkout_user(payload, current_user), _checkout_plan(payload), payload.success_url, payload.cancel_url)


@router.post("/create-one-time-checkout")
async def one_time_checkout(payload: CheckoutRequest, current_user: Optional[CurrentUser] = Depends(get_optional_current_user)) -> Dict[str, Any]:
    return create_one_time_checkout(_checkout_user(payload, current_user), payload.project_id, payload.success_url, payload.cancel_url)


@router.post("/webhook")
async def billing_webhook(request: Request) -> Dict[str, Any]:
    body = await request.body()
    lemon_signature = request.headers.get("x-signature")
    if lemon_signature:
        return handle_webhook(body, lemon_signature, provider_hint="lemonsqueezy")
    return handle_webhook(body, request.headers.get("stripe-signature"), provider_hint="stripe")


@router.get("/status")
async def billing_status(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return {"billing": get_billing_status(current_user)}


@router.get("/usage")
async def billing_usage(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return {"usage": get_usage(current_user)}
