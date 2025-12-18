"""
Unit tests for payment QR code generation API routes.

Tests cover:
- Simple address QR code generation
- Payment request QR with amount, memo, expiry
- Payment request tracking and status checking
- Payment URI parsing and validation
- Expiry validation
- Error handling
"""

from __future__ import annotations

import json
import time
import base64
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from xai.mobile.qr_transactions import (
    TransactionQRGenerator,
    QRCodeValidator,
    QRCODE_AVAILABLE,
)

# Test address (valid format with XAI prefix and hex body)
TEST_ADDRESS = "XAI1234567890abcdef1234567890abcdef12345678"
TEST_ADDRESS_2 = "XAI9876543210fedcba9876543210fedcba98765432"


class TestAddressQRGeneration:
    """Test simple address QR code generation."""

    @patch("xai.core.api_routes.payment.validate_address")
    def test_get_address_qr_image_format(self, mock_validate, client, mock_blockchain):
        """Test generating QR code as PNG image."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        response = client.get(f"/payment/qr/{TEST_ADDRESS}?format=image")
        assert response.status_code == 200
        assert response.content_type == "image/png"
        assert len(response.data) > 0

    @patch("xai.core.api_routes.payment.validate_address")
    def test_get_address_qr_base64_format(self, mock_validate, client, mock_blockchain):
        """Test generating QR code as base64 JSON."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        response = client.get(f"/payment/qr/{TEST_ADDRESS}?format=base64")
        assert response.status_code == 200
        data = response.get_json()
        assert data["address"] == TEST_ADDRESS
        assert "qr_code" in data
        assert data["uri"] == f"xai:{TEST_ADDRESS}"
        assert data["format"] == "base64"

        # Verify it's valid base64
        try:
            base64.b64decode(data["qr_code"])
        except Exception as e:
            pytest.fail(f"Invalid base64 data: {e}")

    @patch("xai.core.api_routes.payment.validate_address")
    def test_get_address_qr_default_format(self, mock_validate, client, mock_blockchain):
        """Test default format is image."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        response = client.get(f"/payment/qr/{TEST_ADDRESS}")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    @patch("xai.core.api_routes.payment.validate_address", side_effect=ValueError("Invalid"))
    def test_get_address_qr_invalid_address(self, mock_validate, client, mock_blockchain):
        """Test error handling for invalid address."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        response = client.get("/payment/qr/invalid_address")
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "invalid_address"


class TestPaymentQRGeneration:
    """Test payment request QR code generation with amount and memo."""

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_qr_minimal(self, mock_validate, client, mock_blockchain):
        """Test creating payment QR with just address."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS,
            "format": "base64"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["address"] == TEST_ADDRESS
        assert "qr_code" in data
        assert data["uri"] == f"xai:{TEST_ADDRESS}"

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_qr_with_amount(self, mock_validate, client, mock_blockchain):
        """Test creating payment QR with amount."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS,
            "amount": "100.50",
            "format": "base64"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["address"] == TEST_ADDRESS
        assert data["amount"] == 100.50
        assert "amount=100.5" in data["uri"]

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_qr_with_memo(self, mock_validate, client, mock_blockchain):
        """Test creating payment QR with memo."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS,
            "amount": "50.00",
            "memo": "Invoice #123",
            "format": "base64"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["memo"] == "Invoice #123"
        assert "memo=" in data["uri"]

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_qr_with_expiry(self, mock_validate, client, mock_blockchain):
        """Test creating payment QR with expiry."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS,
            "amount": "75.00",
            "expiry_minutes": 30,
            "format": "base64"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert "expires_at" in data
        # Check expiry is approximately 30 minutes in future
        expected_expiry = int(time.time()) + (30 * 60)
        assert abs(data["expires_at"] - expected_expiry) < 5  # Within 5 seconds

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_qr_image_format(self, mock_validate, client, mock_blockchain):
        """Test creating payment QR as PNG image."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS,
            "amount": "25.00",
            "format": "image"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 200
        assert response.content_type == "image/png"
        assert len(response.data) > 0

    def test_create_payment_qr_missing_address(self, client, mock_blockchain):
        """Test error handling when address is missing."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "amount": "100.00"
        }
        response = client.post("/payment/qr", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "missing_address"


class TestPaymentRequestTracking:
    """Test payment request creation and tracking."""

    @patch("xai.core.api_routes.payment.validate_address")
    def test_create_payment_request_minimal(self, mock_validate, client, mock_blockchain):
        """Test creating minimal payment request."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS_2,
            "amount": "100.00"
        }
        response = client.post("/payment/request", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert "request_id" in data
        assert data["address"] == TEST_ADDRESS_2
        assert data["amount"] == 100.00
        assert data["status"] == "pending"
        assert "qr_code" in data
        assert "uri" in data
        assert "expires_at" in data  # Default expiry

    def test_create_payment_request_missing_amount(self, client, mock_blockchain):
        """Test error when amount is missing."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "address": TEST_ADDRESS_2
        }
        response = client.post("/payment/request", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "missing_amount"


class TestPaymentRequestStatus:
    """Test payment request status checking."""

    @patch("xai.core.api_routes.payment.validate_address")
    def test_get_payment_request_pending(self, mock_validate, client, mock_blockchain):
        """Test getting payment request in pending status."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        # Create payment request
        payload = {
            "address": TEST_ADDRESS_2,
            "amount": "100.00"
        }
        create_response = client.post("/payment/request", json=payload)
        request_id = create_response.get_json()["request_id"]

        # Get status
        response = client.get(f"/payment/request/{request_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] == request_id
        assert data["status"] == "pending"
        assert data["address"] == TEST_ADDRESS_2
        assert data["amount"] == 100.00

    def test_get_payment_request_not_found(self, client, mock_blockchain):
        """Test error when request ID not found."""
        response = client.get("/payment/request/nonexistent-id")
        assert response.status_code == 404
        data = response.get_json()
        assert data["code"] == "request_not_found"


class TestPaymentURIParsing:
    """Test payment URI parsing and validation."""

    def test_parse_payment_uri_address_only(self, client, mock_blockchain):
        """Test parsing URI with address only."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "uri": f"xai:{TEST_ADDRESS}"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["address"] == TEST_ADDRESS

    def test_parse_payment_uri_with_amount(self, client, mock_blockchain):
        """Test parsing URI with amount."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "uri": f"xai:{TEST_ADDRESS}?amount=100.50"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["address"] == TEST_ADDRESS
        assert data["amount"] == 100.50

    def test_parse_payment_uri_with_memo(self, client, mock_blockchain):
        """Test parsing URI with memo."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "uri": f"xai:{TEST_ADDRESS}?message=Payment%20for%20order"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["memo"] == "Payment for order"

    def test_parse_payment_uri_with_expiry(self, client, mock_blockchain):
        """Test parsing URI with expiry."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        future_timestamp = int(time.time()) + 3600  # 1 hour in future
        payload = {
            "uri": f"xai:{TEST_ADDRESS}?exp={future_timestamp}"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["expires_at"] == future_timestamp
        assert data["expired"] is False

    def test_parse_payment_uri_expired(self, client, mock_blockchain):
        """Test parsing URI with past expiry."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        past_timestamp = int(time.time()) - 3600  # 1 hour in past
        payload = {
            "uri": f"xai:{TEST_ADDRESS}?exp={past_timestamp}"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["expired"] is True

    def test_parse_payment_uri_invalid_format(self, client, mock_blockchain):
        """Test error for invalid URI format."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        payload = {
            "uri": "invalid:format"
        }
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "invalid_uri"

    def test_parse_payment_uri_missing_uri(self, client, mock_blockchain):
        """Test error when URI is missing."""
        payload = {}
        response = client.post("/payment/parse", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "invalid_request"


class TestQRCodeValidator:
    """Test QR code validation functions."""

    def test_validate_payment_uri_valid(self):
        """Test validation of valid payment URI."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        uri = f"xai:{TEST_ADDRESS}?amount=100.50"
        assert QRCodeValidator.validate_payment_uri(uri) is True

    def test_validate_payment_uri_invalid_prefix(self):
        """Test validation fails for invalid prefix."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        uri = f"btc:{TEST_ADDRESS}"
        assert QRCodeValidator.validate_payment_uri(uri) is False

    def test_sanitize_qr_data_valid(self):
        """Test sanitizing valid QR data."""
        data = f"xai:{TEST_ADDRESS}?amount=100"
        sanitized = QRCodeValidator.sanitize_qr_data(data)
        assert sanitized == data

    def test_sanitize_qr_data_too_long(self):
        """Test sanitizing data exceeding max length."""
        data = "x" * 5000
        with pytest.raises(ValueError, match="exceeds maximum length"):
            QRCodeValidator.sanitize_qr_data(data, max_length=4096)

    def test_sanitize_qr_data_non_string(self):
        """Test sanitizing non-string data."""
        with pytest.raises(ValueError, match="must be a string"):
            QRCodeValidator.sanitize_qr_data(123)


class TestPaymentVerification:
    """Test payment verification endpoint."""

    @patch("xai.core.api_routes.payment.validate_address")
    def test_verify_payment_with_request_id(self, mock_validate, client, mock_blockchain):
        """Test verifying payment against a payment request."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        # Create payment request first
        create_payload = {
            "address": TEST_ADDRESS,
            "amount": "100.00"
        }
        create_response = client.post("/payment/request", json=create_payload)
        request_id = create_response.get_json()["request_id"]

        # Verify payment
        verify_payload = {
            "request_id": request_id,
            "txid": "tx123abc",
            "sender": TEST_ADDRESS_2,
            "recipient": TEST_ADDRESS,
            "amount": 100.00,
            "timestamp": int(time.time()),
            "confirmations": 1
        }
        response = client.post("/payment/verify", json=verify_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["verified"] is True
        assert data["request_id"] == request_id
        assert data["status"] == "paid"

    @patch("xai.core.api_routes.payment.validate_address")
    def test_verify_payment_amount_mismatch(self, mock_validate, client, mock_blockchain):
        """Test verification fails for amount mismatch."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        # Create payment request
        create_payload = {
            "address": TEST_ADDRESS,
            "amount": "100.00"
        }
        create_response = client.post("/payment/request", json=create_payload)
        request_id = create_response.get_json()["request_id"]

        # Try to verify with wrong amount
        verify_payload = {
            "request_id": request_id,
            "txid": "tx123abc",
            "recipient": TEST_ADDRESS,
            "amount": 95.00,  # Wrong amount
            "timestamp": int(time.time())
        }
        response = client.post("/payment/verify", json=verify_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert data["verified"] is False
        assert data["error_code"] == "amount_mismatch"

    @patch("xai.core.api_routes.payment.validate_address")
    def test_verify_payment_recipient_mismatch(self, mock_validate, client, mock_blockchain):
        """Test verification fails for recipient mismatch."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        # Create payment request
        create_payload = {
            "address": TEST_ADDRESS,
            "amount": "100.00"
        }
        create_response = client.post("/payment/request", json=create_payload)
        request_id = create_response.get_json()["request_id"]

        # Try to verify with wrong recipient
        verify_payload = {
            "request_id": request_id,
            "txid": "tx123abc",
            "recipient": TEST_ADDRESS_2,  # Wrong address
            "amount": 100.00,
            "timestamp": int(time.time())
        }
        response = client.post("/payment/verify", json=verify_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert data["verified"] is False
        assert data["error_code"] == "recipient_mismatch"

    def test_verify_payment_missing_required_fields(self, client, mock_blockchain):
        """Test verification fails with missing fields."""
        verify_payload = {
            "txid": "tx123abc",
            "recipient": TEST_ADDRESS
            # Missing amount
        }
        response = client.post("/payment/verify", json=verify_payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "missing_amount"

    def test_verify_payment_request_not_found(self, client, mock_blockchain):
        """Test verification fails for nonexistent request."""
        verify_payload = {
            "request_id": "nonexistent-id",
            "txid": "tx123abc",
            "recipient": TEST_ADDRESS,
            "amount": 100.00,
            "timestamp": int(time.time())
        }
        response = client.post("/payment/verify", json=verify_payload)
        assert response.status_code == 404
        data = response.get_json()
        assert data["code"] == "request_not_found"


class TestTransactionQRGenerator:
    """Test TransactionQRGenerator utility functions."""

    def test_generate_address_qr(self):
        """Test generating address QR code."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        qr_data = TransactionQRGenerator.generate_address_qr(TEST_ADDRESS)
        assert qr_data is not None
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(qr_data)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 data: {e}")

    def test_generate_payment_request_qr_with_all_params(self):
        """Test generating payment request QR with all parameters."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        qr_data = TransactionQRGenerator.generate_payment_request_qr(
            address=TEST_ADDRESS,
            amount=250.00,
            label="Merchant",
            message="Invoice #789"
        )
        assert qr_data is not None

    def test_parse_payment_uri_complete(self):
        """Test parsing complete payment URI."""
        if not QRCODE_AVAILABLE:
            pytest.skip("qrcode library not available")

        uri = f"xai:{TEST_ADDRESS}?amount=150.00&label=Store&message=Purchase"
        parsed = TransactionQRGenerator.parse_payment_uri(uri)
        assert parsed["address"] == TEST_ADDRESS
        assert parsed["amount"] == 150.00
        assert parsed["label"] == "Store"
        assert parsed["message"] == "Purchase"

    def test_parse_payment_uri_invalid_prefix(self):
        """Test parsing URI with wrong prefix."""
        with pytest.raises(ValueError, match="Invalid XAI payment URI"):
            TransactionQRGenerator.parse_payment_uri("btc:address")


# Fixtures

@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain instance."""
    blockchain = MagicMock()
    blockchain.chain = []
    return blockchain


@pytest.fixture
def client(mock_blockchain):
    """Create a Flask test client with payment routes."""
    from flask import Flask
    from xai.core.api_routes.payment import register_payment_routes

    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock routes object
    class MockRoutes:
        def __init__(self):
            self.app = app
            self.blockchain = mock_blockchain

    routes = MockRoutes()
    register_payment_routes(routes)

    with app.test_client() as client:
        yield client
