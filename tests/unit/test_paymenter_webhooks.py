"""
BlueHub Paymenter Webhooks Unit Tests
======================================
Tests for HMAC-SHA256 signature verification, idempotency, event storage,
and processing of Paymenter webhook events.

Run: pytest tests/unit/test_paymenter_webhooks.py -v --asyncio-mode=auto
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from core.paymenter.schemas import (
    PaymenterEventPayload,
    PaymenterWebhookResponse,
)
from core.paymenter.service import PaymenterService, paymenter_service
from shared.models.paymenter_webhook import PaymenterWebhookEvent

# ── Constants ───────────────────────────────────────────────────────────────

TEST_SECRET = "test_webhook_secret_key_12345"
TEST_EVENT_ID = "evt_test_event_001"
TEST_EVENT_ID_2 = "evt_test_event_002"
TEST_SIGNATURE_HEADER = "X-Webhook-Signature"


def _compute_signature(payload: bytes, secret: str = TEST_SECRET) -> str:
    """Compute HMAC-SHA256 signature for test payload."""
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={expected}"


def _make_payload(
    event_id: str = TEST_EVENT_ID,
    event_type: str = "user.created",
    data: dict[str, Any] | None = None,
) -> bytes:
    """Create a test webhook payload as JSON bytes."""
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "data": data or {"id": "usr_123", "email": "test@example.com"},
        "timestamp": "2026-06-14T12:00:00Z",
    }
    return json.dumps(payload).encode("utf-8")


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    """Reset service to test configuration before each test."""
    paymenter_service.webhook_secret = TEST_SECRET
    paymenter_service.max_retries = 3
    paymenter_service.signature_header = TEST_SIGNATURE_HEADER


@pytest.fixture
def user_created_payload() -> bytes:
    """Sample user.created webhook payload."""
    return _make_payload(
        event_id=TEST_EVENT_ID,
        event_type="user.created",
        data={"id": "usr_123", "email": "test@example.com", "name": "Test User"},
    )


@pytest.fixture
def payment_succeeded_payload() -> bytes:
    """Sample payment.succeeded webhook payload."""
    return _make_payload(
        event_id=TEST_EVENT_ID_2,
        event_type="payment.succeeded",
        data={
            "user_id": "usr_123",
            "order_id": "ord_456",
            "amount": 29.99,
            "currency": "USD",
            "product": "VPN Monthly",
        },
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock database session."""
    session = AsyncMock()
    # Make execute return a result that has scalar_one_or_none returning None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    return session


# ── Signature Verification Tests ───────────────────────────────────────────


class TestSignatureVerification:
    """Tests for HMAC-SHA256 signature verification."""

    def test_verify_valid_signature(self, user_created_payload: bytes) -> None:
        """Verify that a correctly signed payload passes verification."""
        signature = _compute_signature(user_created_payload)
        assert paymenter_service.verify_signature(user_created_payload, signature) is True

    def test_verify_invalid_signature(self, user_created_payload: bytes) -> None:
        """Verify that an incorrectly signed payload fails verification."""
        signature = "sha256=invalid_signature_here"
        assert paymenter_service.verify_signature(user_created_payload, signature) is False

    def test_verify_tampered_payload(self, user_created_payload: bytes) -> None:
        """Verify that a tampered payload fails verification."""
        signature = _compute_signature(user_created_payload)
        tampered_payload = user_created_payload + b"extra_data"
        assert paymenter_service.verify_signature(tampered_payload, signature) is False

    def test_verify_empty_signature(self, user_created_payload: bytes) -> None:
        """Verify that missing signature fails verification."""
        assert paymenter_service.verify_signature(user_created_payload, "") is False

    def test_verify_no_secret_configured(self, user_created_payload: bytes) -> None:
        """Verify that when no secret is configured, verification is skipped."""
        paymenter_service.webhook_secret = None
        assert paymenter_service.verify_signature(user_created_payload, "") is True

    def test_verify_wrong_secret(self, user_created_payload: bytes) -> None:
        """Verify that a signature from a different secret fails."""
        wrong_secret_signature = _compute_signature(user_created_payload, "wrong_secret")
        assert paymenter_service.verify_signature(user_created_payload, wrong_secret_signature) is False

    def test_verify_different_event_types(
        self, user_created_payload: bytes, payment_succeeded_payload: bytes
    ) -> None:
        """Verify signatures for different event types."""
        sig1 = _compute_signature(user_created_payload)
        sig2 = _compute_signature(payment_succeeded_payload)

        assert paymenter_service.verify_signature(user_created_payload, sig1) is True
        assert paymenter_service.verify_signature(payment_succeeded_payload, sig2) is True
        # Cross-check: sig2 should not validate user_created_payload
        assert paymenter_service.verify_signature(user_created_payload, sig2) is False


# ── Idempotency Tests ──────────────────────────────────────────────────────


class TestIdempotency:
    """Tests for idempotency checking."""

    async def test_no_existing_event(self, mock_session: AsyncMock) -> None:
        """Check that a new event_id returns None."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        existing = await paymenter_service.check_idempotency(mock_session, TEST_EVENT_ID)
        assert existing is None

    async def test_existing_event_found(self, mock_session: AsyncMock) -> None:
        """Check that an existing event is returned."""
        existing_event = MagicMock(spec=PaymenterWebhookEvent)
        existing_event.event_id = TEST_EVENT_ID
        existing_event.processed = True

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_event
        mock_session.execute.return_value = result_mock

        found = await paymenter_service.check_idempotency(mock_session, TEST_EVENT_ID)
        assert found is not None
        assert found.event_id == TEST_EVENT_ID

    async def test_idempotency_multiple_events(self, mock_session: AsyncMock) -> None:
        """Check idempotency with multiple different event IDs."""
        event_ids = ["evt_1", "evt_2", "evt_3"]

        for i, eid in enumerate(event_ids):
            result_mock = MagicMock()
            if i == 1:
                existing = MagicMock(spec=PaymenterWebhookEvent)
                existing.event_id = eid
                result_mock.scalar_one_or_none.return_value = existing
            else:
                result_mock.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = result_mock

            found = await paymenter_service.check_idempotency(mock_session, eid)
            if i == 1:
                assert found is not None
                assert found.event_id == eid
            else:
                assert found is None


# ── Event Storage Tests ────────────────────────────────────────────────────


class TestEventStorage:
    """Tests for storing webhook events in the database."""

    async def test_store_user_created_event(self, mock_session: AsyncMock) -> None:
        """Test storing a user.created event."""
        payload = _make_payload(
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            data={"id": "usr_123", "email": "test@example.com"},
        )
        body_dict = json.loads(payload.decode("utf-8"))
        signature = _compute_signature(payload)

        event = await paymenter_service.store_event(
            session=mock_session,
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            payload=body_dict,
            signature=signature,
        )

        assert event.event_id == TEST_EVENT_ID
        assert event.event_type == "user.created"
        assert event.paymenter_user_id == "usr_123"
        assert event.paymenter_order_id is None

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(event)

    async def test_store_payment_succeeded_event(self, mock_session: AsyncMock) -> None:
        """Test storing a payment.succeeded event."""
        payload = _make_payload(
            event_id=TEST_EVENT_ID_2,
            event_type="payment.succeeded",
            data={
                "user_id": "usr_123",
                "order_id": "ord_456",
                "amount": 29.99,
            },
        )
        body_dict = json.loads(payload.decode("utf-8"))
        signature = _compute_signature(payload)

        event = await paymenter_service.store_event(
            session=mock_session,
            event_id=TEST_EVENT_ID_2,
            event_type="payment.succeeded",
            payload=body_dict,
            signature=signature,
        )

        assert event.event_id == TEST_EVENT_ID_2
        assert event.event_type == "payment.succeeded"
        assert event.paymenter_user_id == "usr_123"
        assert event.paymenter_order_id == "ord_456"

    async def test_store_event_no_reference_ids(self, mock_session: AsyncMock) -> None:
        """Test storing an event without user/order reference IDs."""
        payload = _make_payload(
            event_id="evt_unknown",
            event_type="unknown.event",
            data={"some_key": "some_value"},
        )
        body_dict = json.loads(payload.decode("utf-8"))
        signature = _compute_signature(payload)

        event = await paymenter_service.store_event(
            session=mock_session,
            event_id="evt_unknown",
            event_type="unknown.event",
            payload=body_dict,
            signature=signature,
        )

        assert event.paymenter_user_id is None
        assert event.paymenter_order_id is None


# ── Processing Tests ───────────────────────────────────────────────────────


class TestEventProcessing:
    """Tests for processing webhook events."""

    async def test_process_user_created(self, mock_session: AsyncMock) -> None:
        """Test processing a user.created event."""
        payload_data = {"id": "usr_123", "email": "test@example.com", "name": "Test"}
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            data=payload_data,
        )

        # Should not raise any exception
        await paymenter_service.process_user_created(mock_session, payload)

    async def test_process_payment_succeeded(self, mock_session: AsyncMock) -> None:
        """Test processing a payment.succeeded event."""
        payload_data = {
            "user_id": "usr_123",
            "order_id": "ord_456",
            "amount": 29.99,
            "currency": "USD",
        }
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID_2,
            event_type="payment.succeeded",
            data=payload_data,
        )

        # Should not raise any exception
        await paymenter_service.process_payment_succeeded(mock_session, payload)


# ── Mark Processed Tests ───────────────────────────────────────────────────


class TestMarkProcessed:
    """Tests for marking events as processed."""

    async def test_mark_successful(self, mock_session: AsyncMock) -> None:
        """Test marking an event as successfully processed."""
        event = MagicMock(spec=PaymenterWebhookEvent)
        event.processed = False
        event.processing_attempts = 0
        event.last_error = None

        await paymenter_service.mark_processed(mock_session, event)

        assert event.processed is True
        assert event.processing_attempts == 1
        assert event.processed_at is not None
        mock_session.commit.assert_awaited_once()

    async def test_mark_with_error(self, mock_session: AsyncMock) -> None:
        """Test marking an event with a processing error."""
        event = MagicMock(spec=PaymenterWebhookEvent)
        event.processed = True
        event.processing_attempts = 1
        event.last_error = None

        await paymenter_service.mark_processed(
            mock_session, event, error="Processing failed: connection error"
        )

        assert event.processed is False
        assert event.processing_attempts == 2
        assert event.last_error == "Processing failed: connection error"


# ── Full Webhook Handler Tests ─────────────────────────────────────────────


class TestWebhookHandler:
    """Tests for the main webhook event handler (handle_webhook_event)."""

    async def test_handle_user_created_success(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test successful handling of a user.created webhook."""
        signature = _compute_signature(user_created_payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, user_created_payload, signature
        )

        assert isinstance(response, PaymenterWebhookResponse)
        assert response.status == "processed"
        assert response.event_id == TEST_EVENT_ID
        assert "user.created" in response.message

    async def test_handle_payment_succeeded_success(
        self, mock_session: AsyncMock, payment_succeeded_payload: bytes
    ) -> None:
        """Test successful handling of a payment.succeeded webhook."""
        signature = _compute_signature(payment_succeeded_payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, payment_succeeded_payload, signature
        )

        assert isinstance(response, PaymenterWebhookResponse)
        assert response.status == "processed"
        assert response.event_id == TEST_EVENT_ID_2
        assert "payment.succeeded" in response.message

    async def test_handle_invalid_signature(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test that an invalid signature raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await paymenter_service.handle_webhook_event(
                mock_session, user_created_payload, "sha256=bad_signature"
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "signature" in str(exc_info.value.detail).lower()

    async def test_handle_duplicate_event(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test that duplicate events are detected and return 'duplicate' status."""
        signature = _compute_signature(user_created_payload)

        # First call: process successfully
        response1 = await paymenter_service.handle_webhook_event(
            mock_session, user_created_payload, signature
        )
        assert response1.status == "processed"

        # Second call: simulate duplicate by making check_idempotency return the stored event
        existing_event = MagicMock(spec=PaymenterWebhookEvent)
        existing_event.event_id = TEST_EVENT_ID
        existing_event.processed = True

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_event
        mock_session.execute.return_value = result_mock

        response2 = await paymenter_service.handle_webhook_event(
            mock_session, user_created_payload, signature
        )
        assert response2.status == "duplicate"
        assert response2.event_id == TEST_EVENT_ID

    async def test_handle_duplicate_pending_retry(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test that duplicate events pending retry return 'retry' status."""
        signature = _compute_signature(user_created_payload)

        # Simulate an existing event that was NOT processed (failed)
        existing_event = MagicMock(spec=PaymenterWebhookEvent)
        existing_event.event_id = TEST_EVENT_ID
        existing_event.processed = False

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_event
        mock_session.execute.return_value = result_mock

        response = await paymenter_service.handle_webhook_event(
            mock_session, user_created_payload, signature
        )
        assert response.status == "retry"
        assert response.event_id == TEST_EVENT_ID

    async def test_handle_unknown_event_type(
        self, mock_session: AsyncMock
    ) -> None:
        """Test handling an unknown event type."""
        payload = _make_payload(
            event_id="evt_unknown",
            event_type="unknown.event_type",
            data={"foo": "bar"},
        )
        signature = _compute_signature(payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, payload, signature
        )
        assert response.status == "error"
        assert "unknown" in response.message.lower() or "unsupported" in response.message.lower()

    async def test_handle_processing_exception(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test handling when processing raises an exception."""
        signature = _compute_signature(user_created_payload)

        # Patch process_user_created to raise an exception
        with patch.object(
            paymenter_service, "process_user_created", side_effect=ValueError("DB connection lost")
        ):
            response = await paymenter_service.handle_webhook_event(
                mock_session, user_created_payload, signature
            )
            assert response.status == "error"
            assert "DB connection lost" in response.message

    async def test_handle_empty_body_invalid_signature(self, mock_session: AsyncMock) -> None:
        """Test handling of empty body with invalid signature (should fail before JSON parse)."""
        with pytest.raises(HTTPException) as exc_info:
            await paymenter_service.handle_webhook_event(
                mock_session, b"", "sha256=invalid_signature"
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "signature" in str(exc_info.value.detail).lower()

    async def test_handle_verify_first_fails_before_processing(
        self, mock_session: AsyncMock, user_created_payload: bytes
    ) -> None:
        """Test that verification happens before any processing."""
        # Patch process_user_created to raise assertion if called
        with patch.object(
            paymenter_service, "process_user_created", side_effect=AssertionError("Should not be called")
        ):
            # Bad signature should raise before processing
            with pytest.raises(HTTPException):
                await paymenter_service.handle_webhook_event(
                    mock_session, user_created_payload, "sha256=bad_sig"
                )


# ── Schema Validation Tests ────────────────────────────────────────────────


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_valid_user_created_payload(self) -> None:
        """Test that a valid user.created payload passes schema validation."""
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            data={"id": "usr_123", "email": "test@example.com"},
        )
        assert payload.event_id == TEST_EVENT_ID
        assert payload.event_type == "user.created"
        assert payload.data["id"] == "usr_123"

    def test_valid_payment_succeeded_payload(self) -> None:
        """Test that a valid payment.succeeded payload passes schema validation."""
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID_2,
            event_type="payment.succeeded",
            data={"user_id": "usr_123", "order_id": "ord_456", "amount": 29.99},
        )
        assert payload.event_type == "payment.succeeded"
        assert payload.data["amount"] == 29.99

    def test_payload_with_timestamp(self) -> None:
        """Test payload with optional timestamp field."""
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            data={"id": "usr_123"},
            timestamp="2026-06-14T12:00:00Z",
        )
        assert payload.timestamp == "2026-06-14T12:00:00Z"

    def test_payload_without_timestamp(self) -> None:
        """Test payload without optional timestamp field."""
        payload = PaymenterEventPayload(
            event_id=TEST_EVENT_ID,
            event_type="user.created",
            data={"id": "usr_123"},
        )
        assert payload.timestamp is None

    def test_webhook_response_schema(self) -> None:
        """Test PaymenterWebhookResponse schema."""
        response = PaymenterWebhookResponse(
            status="processed",
            message="Event processed successfully",
            event_id=TEST_EVENT_ID,
        )
        assert response.status == "processed"
        assert response.event_id == TEST_EVENT_ID

    def test_webhook_response_duplicate(self) -> None:
        """Test duplicate webhook response."""
        response = PaymenterWebhookResponse(
            status="duplicate",
            message="Webhook event already processed",
            event_id=TEST_EVENT_ID,
        )
        assert response.status == "duplicate"

    def test_webhook_response_error(self) -> None:
        """Test error webhook response."""
        response = PaymenterWebhookResponse(
            status="error",
            message="Processing failed: connection error",
            event_id=TEST_EVENT_ID,
        )
        assert response.status == "error"


# ── Service Configuration Tests ────────────────────────────────────────────


class TestServiceConfiguration:
    """Tests for PaymenterService initialization and configuration."""

    def test_service_singleton(self) -> None:
        """Test that paymenter_service is a singleton."""
        assert isinstance(paymenter_service, PaymenterService)

    def test_default_configuration(self) -> None:
        """Test default service configuration values."""
        service = PaymenterService()
        assert service.max_retries > 0
        assert service.signature_header is not None

    def test_configuration_with_custom_values(self) -> None:
        """Test service with custom configuration values."""
        service = PaymenterService()
        service.webhook_secret = "custom_secret"
        service.max_retries = 5
        service.signature_header = "X-Custom-Signature"

        assert service.webhook_secret == "custom_secret"
        assert service.max_retries == 5
        assert service.signature_header == "X-Custom-Signature"


# ── Edge Case Tests ────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_large_payload(self, mock_session: AsyncMock) -> None:
        """Test handling of large payloads."""
        large_data = {"key": "x" * 10000}  # 10KB string
        payload = _make_payload(
            event_id="evt_large",
            event_type="user.created",
            data=large_data,
        )
        signature = _compute_signature(payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, payload, signature
        )
        assert response.status == "processed"

    async def test_payload_with_special_characters(self, mock_session: AsyncMock) -> None:
        """Test handling of payloads with special characters."""
        special_data = {
            "id": "usr_123",
            "email": "test+alias@example.com",
            "name": "Tést Üser 🎉",
            "notes": "Line 1\nLine 2\nSpecial: !@#$%^&*()",
        }
        payload = _make_payload(
            event_id="evt_special",
            event_type="user.created",
            data=special_data,
        )
        signature = _compute_signature(payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, payload, signature
        )
        assert response.status == "processed"

    async def test_payload_with_nested_data(self, mock_session: AsyncMock) -> None:
        """Test handling of deeply nested payload data."""
        nested_data = {
            "id": "usr_123",
            "metadata": {
                "profile": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": {
                        "street": "123 Main St",
                        "city": "New York",
                        "country": "USA",
                    },
                },
                "tags": ["premium", "vip", "beta_tester"],
            },
        }
        payload = _make_payload(
            event_id="evt_nested",
            event_type="user.created",
            data=nested_data,
        )
        signature = _compute_signature(payload)

        response = await paymenter_service.handle_webhook_event(
            mock_session, payload, signature
        )
        assert response.status == "processed"

    async def test_multiple_events_sequential(
        self, mock_session: AsyncMock
    ) -> None:
        """Test handling multiple events in sequence."""
        events = [
            ("evt_seq_1", "user.created", {"id": "usr_1"}),
            ("evt_seq_2", "payment.succeeded", {"user_id": "usr_1", "order_id": "ord_1", "amount": 10}),
            ("evt_seq_3", "user.created", {"id": "usr_2"}),
            ("evt_seq_4", "payment.succeeded", {"user_id": "usr_2", "order_id": "ord_2", "amount": 20}),
        ]

        for event_id, event_type, data in events:
            payload = _make_payload(event_id=event_id, event_type=event_type, data=data)
            signature = _compute_signature(payload)

            # Reset mock for each event (simulate no existing events)
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = result_mock

            response = await paymenter_service.handle_webhook_event(
                mock_session, payload, signature
            )
            assert response.status == "processed"
            assert response.event_id == event_id


__all__ = []