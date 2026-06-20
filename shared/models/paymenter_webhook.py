"""
BlueHub Paymenter Webhook Event Model
======================================
Stores incoming webhook events for idempotency checking, audit trail,
and retry tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import CoreBase


class PaymenterWebhookEvent(CoreBase):
    """
    Stores received Paymenter webhook events for idempotency and replay protection.
    """

    __tablename__ = "paymenter_webhook_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique event ID from Paymenter for idempotency",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Event type (e.g. user.created, payment.succeeded)",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Raw event payload from Paymenter",
    )
    signature: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="HMAC-SHA256 signature from the request",
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the event has been processed",
    )
    processing_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of processing attempts",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message if processing failed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paymenter_user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Paymenter user ID from the event for cross-reference",
    )
    paymenter_order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Paymenter order ID from the event for cross-reference",
    )


__all__ = ["PaymenterWebhookEvent"]
