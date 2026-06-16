"""
BlueHub Paymenter Webhook Schemas
===================================
Pydantic models for Paymenter webhook request/response handling.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PaymenterEventPayload(BaseModel):
    """
    Schema representing a Paymenter webhook event payload.
    Validates the structure of incoming webhook events.
    """

    event_id: str = Field(
        ...,
        description="Unique event identifier from Paymenter",
        examples=["evt_abc123def456"],
    )
    event_type: str = Field(
        ...,
        description="Type of webhook event",
        examples=["user.created", "payment.succeeded"],
    )
    data: dict[str, Any] = Field(
        ...,
        description="Event-specific data payload",
    )
    timestamp: str | None = Field(
        None,
        description="ISO 8601 timestamp of when the event was created",
        examples=["2026-06-14T12:00:00Z"],
    )


class PaymenterWebhookResponse(BaseModel):
    """
    Standard response schema for webhook endpoints.
    """

    status: str = Field(
        ...,
        description="Processing status: received, processed, duplicate, or error",
        examples=["received"],
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
        examples=["Webhook event received and queued for processing"],
    )
    event_id: str = Field(
        ...,
        description="Unique event identifier",
        examples=["evt_abc123def456"],
    )


__all__ = [
    "PaymenterEventPayload",
    "PaymenterWebhookResponse",
]