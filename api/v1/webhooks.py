"""
BlueHub API Webhooks Router
===========================
Webhook endpoints for external service integrations.
Currently implements Paymenter webhooks for user.created and payment.succeeded events.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.paymenter import PaymenterWebhookResponse, paymenter_service
from dependencies.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/paymenter/user.created",
    response_model=PaymenterWebhookResponse,
    summary="Handle Paymenter user.created webhook",
    description="Receives and processes user creation events from Paymenter.",
    responses={
        200: {"description": "Webhook processed successfully"},
        401: {"description": "Invalid webhook signature"},
        422: {"description": "Invalid webhook payload"},
    },
)
async def paymenter_user_created_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Handle Paymenter user.created webhook event.

    Verifies HMAC-SHA256 signature, checks idempotency, stores the event,
    and processes user creation.
    """
    raw_body = await request.body()
    signature = request.headers.get(settings.WEBHOOK_SIGNATURE_HEADER, "")
    return await paymenter_service.handle_webhook_event(session, raw_body, signature)


@router.post(
    "/paymenter/payment.succeeded",
    response_model=PaymenterWebhookResponse,
    summary="Handle Paymenter payment.succeeded webhook",
    description="Receives and processes payment success events from Paymenter.",
    responses={
        200: {"description": "Webhook processed successfully"},
        401: {"description": "Invalid webhook signature"},
        422: {"description": "Invalid webhook payload"},
    },
)
async def paymenter_payment_succeeded_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Handle Paymenter payment.succeeded webhook event.

    Verifies HMAC-SHA256 signature, checks idempotency, stores the event,
    and processes payment success.
    """
    raw_body = await request.body()
    signature = request.headers.get(settings.WEBHOOK_SIGNATURE_HEADER, "")
    return await paymenter_service.handle_webhook_event(session, raw_body, signature)


__all__ = ["router"]