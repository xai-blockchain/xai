"""
Unit tests for MerchantPaymentProcessor.

Tests cover:
- Payment request creation and validation
- Payment status updates and confirmations
- Payment verification logic
- Webhook generation and delivery
- Webhook signature verification
- Expiration handling
- Event handlers
- Statistics tracking
"""

from __future__ import annotations

import json
import time
import hmac
import hashlib
from unittest.mock import MagicMock, patch, call
from typing import Any

import pytest

from xai.merchant.payment_processor import (
    MerchantPaymentProcessor,
    PaymentRequest,
    PaymentStatus,
    WebhookEvent,
    WebhookDeliveryStatus,
    WebhookDelivery,
)


class TestPaymentRequestCreation:
    """Test payment request creation and validation."""

    def test_create_payment_request_minimal(self, processor):
        """Test creating minimal payment request."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        assert payment_request is not None
        assert payment_request.merchant_id == "TEST_MERCHANT"
        assert payment_request.amount == 100.0
        assert payment_request.status == PaymentStatus.PENDING
        assert payment_request.expires_at is not None
        assert len(payment_request.request_id) > 0

    def test_create_payment_request_full(self, processor):
        """Test creating payment request with all parameters."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=250.50,
            memo="Order #12345",
            invoice_id="INV-001",
            customer_id="CUST-999",
            expiry_minutes=30,
            webhook_url="https://merchant.com/webhook",
            metadata={"order_type": "online", "priority": "high"},
            required_confirmations=12
        )

        assert payment_request.amount == 250.50
        assert payment_request.memo == "Order #12345"
        assert payment_request.invoice_id == "INV-001"
        assert payment_request.customer_id == "CUST-999"
        assert payment_request.webhook_url == "https://merchant.com/webhook"
        assert payment_request.metadata["order_type"] == "online"
        assert payment_request.required_confirmations == 12

        # Check expiry is approximately 30 minutes from now
        expected_expiry = int(time.time()) + (30 * 60)
        assert abs(payment_request.expires_at - expected_expiry) < 5

    def test_create_payment_request_invalid_address(self, processor):
        """Test error for invalid address."""
        with pytest.raises(ValueError, match="Invalid XAI address"):
            processor.create_payment_request(
                address="BTC1234567890",
                amount=100.0
            )

    def test_create_payment_request_invalid_amount(self, processor):
        """Test error for invalid amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            processor.create_payment_request(
                address="XAI1234567890abcdef1234567890abcdef12345678",
                amount=-50.0
            )

        with pytest.raises(ValueError, match="Amount must be positive"):
            processor.create_payment_request(
                address="XAI1234567890abcdef1234567890abcdef12345678",
                amount=0.0
            )

    def test_create_payment_request_memo_too_long(self, processor):
        """Test error for memo exceeding limit."""
        long_memo = "x" * 1001
        with pytest.raises(ValueError, match="Memo exceeds 1000 characters"):
            processor.create_payment_request(
                address="XAI1234567890abcdef1234567890abcdef12345678",
                amount=100.0,
                memo=long_memo
            )


class TestPaymentStatusUpdates:
    """Test payment status updates and tracking."""

    def test_update_payment_status_first_payment(self, processor):
        """Test updating status when payment is first received."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        assert payment_request.status == PaymentStatus.PENDING
        assert payment_request.paid_txid is None

        # Update with payment
        success = processor.update_payment_status(
            request_id=payment_request.request_id,
            txid="tx123abc",
            confirmations=1
        )

        assert success is True
        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.status == PaymentStatus.PAID
        assert updated.paid_txid == "tx123abc"
        assert updated.confirmations == 1
        assert updated.paid_at is not None

    def test_update_payment_status_confirmations(self, processor):
        """Test updating confirmations until fully confirmed."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0,
            required_confirmations=6
        )

        # Initial payment
        processor.update_payment_status(
            request_id=payment_request.request_id,
            txid="tx123abc",
            confirmations=1
        )

        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.is_confirmed() is False

        # Add more confirmations
        processor.update_payment_status(
            request_id=payment_request.request_id,
            txid="tx123abc",
            confirmations=6
        )

        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.is_confirmed() is True
        assert updated.confirmed_at is not None

    def test_update_payment_status_nonexistent(self, processor):
        """Test updating nonexistent payment request."""
        success = processor.update_payment_status(
            request_id="nonexistent-id",
            txid="tx123abc",
            confirmations=1
        )

        assert success is False

    def test_update_payment_status_expired(self, processor):
        """Test updating expired payment request."""
        # Create payment that expires immediately
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0,
            expiry_minutes=0  # Expires immediately
        )

        time.sleep(1)  # Wait for expiry

        # Try to update
        success = processor.update_payment_status(
            request_id=payment_request.request_id,
            txid="tx123abc",
            confirmations=1
        )

        assert success is False
        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.status == PaymentStatus.EXPIRED


class TestPaymentVerification:
    """Test payment verification logic."""

    def test_verify_payment_valid(self, processor):
        """Test verifying valid payment."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        result = processor.verify_payment(
            request_id=payment_request.request_id,
            txid="tx123abc",
            amount=100.0,
            recipient="XAI1234567890abcdef1234567890abcdef12345678"
        )

        assert result["valid"] is True
        assert result["request_id"] == payment_request.request_id

    def test_verify_payment_amount_mismatch(self, processor):
        """Test verification fails for amount mismatch."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        result = processor.verify_payment(
            request_id=payment_request.request_id,
            txid="tx123abc",
            amount=95.0,  # Wrong amount
            recipient="XAI1234567890abcdef1234567890abcdef12345678"
        )

        assert result["valid"] is False
        assert result["error_code"] == "amount_mismatch"
        assert result["expected"] == 100.0
        assert result["received"] == 95.0

    def test_verify_payment_recipient_mismatch(self, processor):
        """Test verification fails for recipient mismatch."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        result = processor.verify_payment(
            request_id=payment_request.request_id,
            txid="tx123abc",
            amount=100.0,
            recipient="XAI9876543210fedcba9876543210fedcba98765432"  # Wrong address
        )

        assert result["valid"] is False
        assert result["error_code"] == "recipient_mismatch"

    def test_verify_payment_expired(self, processor):
        """Test verification fails for expired request."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0,
            expiry_minutes=0
        )

        time.sleep(1)

        result = processor.verify_payment(
            request_id=payment_request.request_id,
            txid="tx123abc",
            amount=100.0,
            recipient="XAI1234567890abcdef1234567890abcdef12345678"
        )

        assert result["valid"] is False
        assert result["error_code"] == "request_expired"

    def test_verify_payment_not_found(self, processor):
        """Test verification fails for nonexistent request."""
        result = processor.verify_payment(
            request_id="nonexistent-id",
            txid="tx123abc",
            amount=100.0,
            recipient="XAI1234567890abcdef1234567890abcdef12345678"
        )

        assert result["valid"] is False
        assert result["error_code"] == "request_not_found"


class TestPaymentCancellation:
    """Test payment request cancellation."""

    def test_cancel_payment_request(self, processor):
        """Test cancelling pending payment request."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        assert payment_request.status == PaymentStatus.PENDING

        success = processor.cancel_payment_request(payment_request.request_id)
        assert success is True

        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.status == PaymentStatus.CANCELLED

    def test_cancel_paid_payment_request(self, processor):
        """Test cannot cancel paid payment request."""
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        # Mark as paid
        processor.update_payment_status(
            request_id=payment_request.request_id,
            txid="tx123abc",
            confirmations=1
        )

        # Try to cancel
        success = processor.cancel_payment_request(payment_request.request_id)
        assert success is False

        updated = processor.get_payment_request(payment_request.request_id)
        assert updated.status == PaymentStatus.PAID


class TestExpirationHandling:
    """Test automatic expiration handling."""

    def test_check_expired_payments(self, processor):
        """Test checking and marking expired payments."""
        # Create expired payment
        payment_request1 = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0,
            expiry_minutes=0
        )

        # Create non-expired payment
        payment_request2 = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=200.0,
            expiry_minutes=60
        )

        time.sleep(1)

        # Check for expired payments
        expired = processor.check_expired_payments()

        assert payment_request1.request_id in expired
        assert payment_request2.request_id not in expired

        # Verify status updated
        updated1 = processor.get_payment_request(payment_request1.request_id)
        assert updated1.status == PaymentStatus.EXPIRED

        updated2 = processor.get_payment_request(payment_request2.request_id)
        assert updated2.status == PaymentStatus.PENDING


class TestWebhookSignature:
    """Test webhook signature generation and verification."""

    def test_generate_webhook_signature(self, processor):
        """Test generating webhook signature."""
        payload = {"event": "payment.created", "data": {"amount": 100.0}}
        signature = processor._generate_webhook_signature(payload, "test_secret")

        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex is 64 chars

    def test_verify_webhook_signature_valid(self, processor):
        """Test verifying valid webhook signature."""
        payload = {"event": "payment.created", "data": {"amount": 100.0}}
        signature = processor._generate_webhook_signature(payload, "test_secret")

        is_valid = processor.verify_webhook_signature(payload, signature, "test_secret")
        assert is_valid is True

    def test_verify_webhook_signature_invalid(self, processor):
        """Test verifying invalid webhook signature."""
        payload = {"event": "payment.created", "data": {"amount": 100.0}}
        wrong_signature = "0" * 64

        is_valid = processor.verify_webhook_signature(payload, wrong_signature, "test_secret")
        assert is_valid is False

    def test_verify_webhook_signature_tampered(self, processor):
        """Test verification fails if payload is tampered."""
        payload = {"event": "payment.created", "data": {"amount": 100.0}}
        signature = processor._generate_webhook_signature(payload, "test_secret")

        # Tamper with payload
        payload["data"]["amount"] = 200.0

        is_valid = processor.verify_webhook_signature(payload, signature, "test_secret")
        assert is_valid is False


class TestEventHandlers:
    """Test event handler registration and triggering."""

    def test_register_event_handler(self, processor):
        """Test registering event handler."""
        handler_called = []

        def handler(payment_request):
            handler_called.append(payment_request.request_id)

        processor.on_event(WebhookEvent.PAYMENT_CREATED, handler)

        # Create payment (should trigger handler)
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        assert payment_request.request_id in handler_called

    def test_multiple_event_handlers(self, processor):
        """Test multiple handlers for same event."""
        handler1_called = []
        handler2_called = []

        def handler1(payment_request):
            handler1_called.append(payment_request.request_id)

        def handler2(payment_request):
            handler2_called.append(payment_request.request_id)

        processor.on_event(WebhookEvent.PAYMENT_CREATED, handler1)
        processor.on_event(WebhookEvent.PAYMENT_CREATED, handler2)

        # Create payment
        payment_request = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        assert payment_request.request_id in handler1_called
        assert payment_request.request_id in handler2_called


class TestStatistics:
    """Test statistics tracking."""

    def test_get_statistics(self, processor):
        """Test getting processor statistics."""
        # Create various payment requests
        pr1 = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=100.0
        )

        pr2 = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=200.0,
            expiry_minutes=0
        )

        pr3 = processor.create_payment_request(
            address="XAI1234567890abcdef1234567890abcdef12345678",
            amount=300.0
        )

        # Update statuses
        processor.update_payment_status(pr1.request_id, "tx1", 1)
        processor.cancel_payment_request(pr3.request_id)
        time.sleep(1)
        processor.check_expired_payments()

        # Get statistics
        stats = processor.get_statistics()

        assert stats["merchant_id"] == "TEST_MERCHANT"
        assert stats["payment_requests"]["total"] == 3
        assert stats["payment_requests"]["paid"] == 1
        assert stats["payment_requests"]["cancelled"] == 1
        assert stats["payment_requests"]["expired"] == 1


# Fixtures

@pytest.fixture
def processor():
    """Create a merchant payment processor for testing."""
    return MerchantPaymentProcessor(
        merchant_id="TEST_MERCHANT",
        webhook_secret="test_webhook_secret",
        default_expiry_minutes=60,
        required_confirmations=6
    )


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library for webhook delivery testing."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr("xai.merchant.payment_processor.requests.post", mock_post)

    return mock_post
