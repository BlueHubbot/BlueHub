"""
BlueHub Paymenter Webhook Service
===================================
Handles HMAC-SHA256 signature verification, idempotency checks,
event logging, and processing of Paymenter webhook events.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.paymenter.schemas import (
    PaymenterEventPayload,
    PaymenterWebhookResponse,
)
from shared.models.paymenter_webhook import PaymenterWebhookEvent

logger = logging.getLogger(__name__)


class PaymenterService:
    """
    Service for processing Paymenter webhook events.
    Handles signature verification, idempotency, and event storage.
    """

    def __init__(self) -> None:
        self.webhook_secret: str | None = settings.PAYMENTER_WEBHOOK_SECRET
        self.max_retries: int = settings.WEBHOOK_MAX_RETRIES
        self.signature_header: str = settings.WEBHOOK_SIGNATURE_HEADER

    def verify_signature(self, payload_body: bytes, signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature of the webhook payload.

        Args:
            payload_body: Raw request body as bytes
            signature: HMAC-SHA256 signature from X-Webhook-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("PAYMENTER_WEBHOOK_SECRET is not configured, skipping verification")
            return True  # Allow in dev/skip if not configured

        if not signature:
            logger.warning("Missing webhook signature header")
            return False

        secret_bytes = self.webhook_secret.encode("utf-8")
        expected = hmac.new(
            secret_bytes,
            payload_body,
            hashlib.sha256,
        ).hexdigest()

        # Use hmac.compare_digest for timing-safe comparison
        return hmac.compare_digest(f"sha256={expected}", signature)

    async def check_idempotency(
        self, session: AsyncSession, event_id: str
    ) -> PaymenterWebhookEvent | None:
        """
        Check if an event has already been received (idempotency check).

        Args:
            session: Database session
            event_id: Unique event ID from Paymenter

        Returns:
            Existing PaymenterWebhookEvent if already processed, None otherwise
        """
        result = await session.execute(
            select(PaymenterWebhookEvent).where(
                PaymenterWebhookEvent.event_id == event_id
            )
        )
        return result.scalar_one_or_none()

    async def store_event(
        self,
        session: AsyncSession,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature: str,
    ) -> PaymenterWebhookEvent:
        """
        Store a webhook event in the database.

        Args:
            session: Database session
            event_id: Unique event ID from Paymenter
            event_type: Type of webhook event
            payload: Raw event payload
            signature: HMAC-SHA256 signature

        Returns:
            The stored PaymenterWebhookEvent record
        """
        # Extract known reference IDs from payload data if present
        data = payload.get("data", {})
        paymenter_user_id: str | None = None
        paymenter_order_id: str | None = None

        if event_type == "user.created":
            paymenter_user_id = str(data.get("id", "")) or None
        elif event_type == "payment.succeeded":
            paymenter_user_id = str(data.get("user_id", "")) or None
            paymenter_order_id = str(data.get("order_id", "")) or None

        event = PaymenterWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            signature=signature,
            paymenter_user_id=paymenter_user_id,
            paymenter_order_id=paymenter_order_id,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    async def mark_processed(
        self,
        session: AsyncSession,
        event: PaymenterWebhookEvent,
        error: str | None = None,
    ) -> None:
        """
        Mark an event as processed (or record a processing error).

        Args:
            session: Database session
            event: The PaymenterWebhookEvent to update
            error: Error message if processing failed, None if successful
        """
        if error:
            event.processed = False
            event.processing_attempts = (event.processing_attempts or 0) + 1
            event.last_error = error
        else:
            event.processed = True
            event.processed_at = datetime.now(UTC)
            event.processing_attempts = (event.processing_attempts or 0) + 1

        await session.commit()

    async def process_user_created(
        self, session: AsyncSession, payload: PaymenterEventPayload
    ) -> None:
        """
        Process a user.created webhook event.
        In a real implementation, this would create a local user record
        or link an existing user with the Paymenter user ID.

        Args:
            session: Database session
            payload: Validated webhook event payload
        """
        user_data = payload.data
        paymenter_user_id = user_data.get("id")
        email = user_data.get("email", "unknown@paymenter.local")

        logger.info(
            "Processing Paymenter user.created event: user_id=%s, email=%s",
            paymenter_user_id,
            email,
        )

        # TODO: Actual implementation - create/link user in the local database
        # For now, this is a stub that logs and succeeds
        logger.info(
            "Paymenter user %s (%s) recorded successfully",
            paymenter_user_id,
            email,
        )

    async def process_payment_succeeded(
        self, session: AsyncSession, payload: PaymenterEventPayload
    ) -> None:
        """
        Process a payment.succeeded webhook event.
        In a real implementation, this would update billing records,
        activate services, etc.

        Args:
            session: Database session
            payload: Validated webhook event payload
        """
        payment_data = payload.data
        paymenter_user_id = payment_data.get("user_id")
        paymenter_order_id = payment_data.get("order_id")
        amount = payment_data.get("amount", 0)
        currency = payment_data.get("currency", "USD")

        logger.info(
            "Processing Paymenter payment.succeeded event: "
            "user_id=%s, order_id=%s, amount=%s %s",
            paymenter_user_id,
            paymenter_order_id,
            amount,
            currency,
        )

        # TODO: Actual implementation - update invoice/transaction records
        # For now, this is a stub that logs and succeeds
        logger.info(
            "Payment of %s %s for order %s recorded successfully",
            amount,
            currency,
            paymenter_order_id,
        )

    async def handle_webhook_event(
        self,
        session: AsyncSession,
        raw_body: bytes,
        signature: str,
    ) -> PaymenterWebhookResponse:
        """
        Main entry point for handling an incoming webhook.
        Verifies signature, checks idempotency, stores the event,
        and triggers processing.

        Args:
            session: Database session
            raw_body: Raw request body as bytes
            signature: HMAC-SHA256 signature from header

        Returns:
            PaymenterWebhookResponse indicating the result

        Raises:
            HTTPException: If signature verification fails
        """
        from fastapi import HTTPException, status

        # 1. Verify signature
        if not self.verify_signature(raw_body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # 2. Parse the payload
        body_str = raw_body.decode("utf-8")
        body_dict: dict[str, Any] = json.loads(body_str)
        event = PaymenterEventPayload.model_validate(body_dict)

        # 3. Check idempotency
        existing = await self.check_idempotency(session, event.event_id)
        if existing:
            if existing.processed:
                logger.info(
                    "Duplicate webhook event received (already processed): %s",
                    event.event_id,
                )
                return PaymenterWebhookResponse(
                    status="duplicate",
                    message="Webhook event has already been processed",
                    event_id=event.event_id,
                )
            else:
                logger.warning(
                    "Duplicate webhook event received (pending retry): %s",
                    event.event_id,
                )
                return PaymenterWebhookResponse(
                    status="retry",
                    message="Webhook event is already queued for retry",
                    event_id=event.event_id,
                )

        # 4. Store the event
        stored = await self.store_event(
            session=session,
            event_id=event.event_id,
            event_type=event.event_type,
            payload=body_dict,
            signature=signature,
        )

        try:
            # 5. Process based on event type
            if event.event_type == "user.created":
                await self.process_user_created(session, event)
            elif event.event_type == "payment.succeeded":
                await self.process_payment_succeeded(session, event)
            else:
                logger.warning("Unknown webhook event type: %s", event.event_type)
                await self.mark_processed(
                    session, stored, error=f"Unknown event type: {event.event_type}"
                )
                return PaymenterWebhookResponse(
                    status="error",
                    message=f"Unsupported event type: {event.event_type}",
                    event_id=event.event_id,
                )

            # 6. Mark as processed
            await self.mark_processed(session, stored)

            logger.info(
                "Webhook event processed successfully: %s (%s)",
                event.event_id,
                event.event_type,
            )

            return PaymenterWebhookResponse(
                status="processed",
                message=f"Webhook event {event.event_type} processed successfully",
                event_id=event.event_id,
            )

        except Exception as exc:
            logger.exception(
                "Failed to process webhook event: %s", event.event_id
            )
            await self.mark_processed(
                session, stored, error=str(exc)
            )
            return PaymenterWebhookResponse(
                status="error",
                message=f"Processing failed: {exc}",
                event_id=event.event_id,
            )


# Singleton instance
paymenter_service = PaymenterService()

__all__ = [
    "PaymenterService",
    "paymenter_service",
]
