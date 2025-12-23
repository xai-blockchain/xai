"""
Payment API Blueprint

Handles payment QR code generation, payment request tracking, and payment verification.
Extracted from api_routes/payment.py as part of route reorganization.

Endpoints:
- GET /payment/qr/<address> - Generate simple address QR code (PNG image)
- POST /payment/qr - Generate payment request QR with amount, memo, expiry
- POST /payment/request - Create a tracked payment request
- GET /payment/request/<request_id> - Check payment request status
- POST /payment/parse - Parse a payment URI from QR code
- POST /payment/verify - Verify a payment against a payment request
"""

from __future__ import annotations

import logging
import time
import uuid
from io import BytesIO
from typing import Any
from urllib.parse import quote, unquote

from flask import Blueprint, Response, jsonify, request, send_file

from xai.core.api_blueprints.base import error_response, get_blockchain
from xai.core.validation import validate_address
from xai.mobile.qr_transactions import (
    QRCODE_AVAILABLE,
    QRCodeValidator,
    TransactionQRGenerator,
)

logger = logging.getLogger(__name__)

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")

# In-memory storage for payment requests (in production, use Redis or database)
_payment_requests: dict[str, dict[str, Any]] = {}

@payment_bp.route("/qr/<address>", methods=["GET"])
def get_address_qr(address: str) -> Response:
    """Generate simple QR code for a blockchain address.

    Returns a PNG image containing a QR code that encodes the address
    in the format: xai:<address>

    Path Parameters:
        address (str): The blockchain address to encode

    Query Parameters:
        format (str, optional): Response format - 'image' (default) or 'base64'

    Returns:
        PNG image (image/png) if format=image, or
        JSON with base64 encoded QR if format=base64

    Raises:
        400: If address is invalid or QR code library unavailable
        500: If QR generation fails
    """
    if not QRCODE_AVAILABLE:
        return jsonify({
            "error": "QR code generation not available",
            "detail": "qrcode library not installed. Install with: pip install qrcode[pil]",
            "code": "qrcode_unavailable"
        }), 400

    # Validate address format
    try:
        validate_address(address)
    except ValueError as e:
        return jsonify({
            "error": "Invalid address",
            "detail": str(e),
            "code": "invalid_address"
        }), 400

    # Get response format
    response_format = request.args.get("format", "image")

    try:
        # Generate QR code
        qr_data = TransactionQRGenerator.generate_address_qr(
            address=address,
            return_format="bytes" if response_format == "image" else "base64"
        )

        if response_format == "image":
            # Return as PNG image
            return send_file(
                BytesIO(qr_data),
                mimetype="image/png",
                as_attachment=False,
                download_name=f"xai_{address[:8]}.png"
            )
        else:
            # Return as base64 JSON
            return jsonify({
                "address": address,
                "qr_code": qr_data,
                "uri": f"xai:{address}",
                "format": "base64"
            })

    except Exception as e:
        logger.error(
            "QR code generation failed",
            extra={"address": address, "error": str(e), "event": "qr.generation_failed"}
        )
        return jsonify({
            "error": "QR generation failed",
            "detail": str(e),
            "code": "qr_generation_error"
        }), 500

@payment_bp.route("/qr", methods=["POST"])
def create_payment_qr() -> tuple[Response, int]:
    """Generate payment request QR code with amount, memo, and expiry.

    Request Body (JSON):
        {
            "address": "XAI1...",           # Required: recipient address
            "amount": "100.50",             # Optional: payment amount
            "memo": "Invoice #123",         # Optional: payment memo
            "expiry_minutes": 30,           # Optional: expiry time (default: no expiry)
            "format": "image"               # Optional: 'image' or 'base64' (default: base64)
        }

    Returns:
        If format='image': PNG image (image/png)
        If format='base64': JSON with QR code data

    Raises:
        400: If request data is invalid
        500: If QR generation fails
    """
    if not QRCODE_AVAILABLE:
        return jsonify({
            "error": "QR code generation not available",
            "detail": "qrcode library not installed",
            "code": "qrcode_unavailable"
        }), 400

    data = request.get_json()
    if not data:
        return jsonify({
            "error": "Invalid request",
            "detail": "JSON body required",
            "code": "invalid_request"
        }), 400

    # Extract and validate required fields
    address = data.get("address")
    if not address:
        return jsonify({
            "error": "Missing required field",
            "detail": "address is required",
            "code": "missing_address"
        }), 400

    try:
        validate_address(address)
    except ValueError as e:
        return jsonify({
            "error": "Invalid address",
            "detail": str(e),
            "code": "invalid_address"
        }), 400

    # Extract optional fields
    amount = data.get("amount")
    memo = data.get("memo", "")
    expiry_minutes = data.get("expiry_minutes")
    response_format = data.get("format", "base64")

    # Validate amount if provided
    if amount is not None:
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({
                    "error": "Invalid amount",
                    "detail": "Amount must be positive",
                    "code": "invalid_amount"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "error": "Invalid amount",
                "detail": "Amount must be a valid number",
                "code": "invalid_amount"
            }), 400

    # Validate memo length
    if memo and len(memo) > 1000:
        return jsonify({
            "error": "Invalid memo",
            "detail": "Memo exceeds 1000 characters",
            "code": "memo_too_long"
        }), 400

    # Calculate expiry timestamp
    expires_at = None
    if expiry_minutes is not None:
        try:
            expiry_minutes = int(expiry_minutes)
            if expiry_minutes <= 0:
                return jsonify({
                    "error": "Invalid expiry",
                    "detail": "Expiry must be positive",
                    "code": "invalid_expiry"
                }), 400
            expires_at = int(time.time()) + (expiry_minutes * 60)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Invalid expiry",
                "detail": "Expiry must be a valid integer",
                "code": "invalid_expiry"
            }), 400

    try:
        # Build payment URI
        uri = f"xai:{address}"
        params = []
        if amount is not None:
            params.append(f"amount={amount}")
        if memo:
            params.append(f"memo={quote(memo)}")
        if expires_at is not None:
            params.append(f"exp={expires_at}")

        if params:
            uri += "?" + "&".join(params)

        # Generate QR code
        qr_data = TransactionQRGenerator.generate_payment_request_qr(
            address=address,
            amount=amount,
            label=None,
            message=memo if memo else None,
            return_format="bytes" if response_format == "image" else "base64"
        )

        if response_format == "image":
            # Return as PNG image
            return send_file(
                BytesIO(qr_data),
                mimetype="image/png",
                as_attachment=False,
                download_name=f"xai_payment_{address[:8]}.png"
            ), 200
        else:
            # Return as base64 JSON
            response_data = {
                "qr_code": qr_data,
                "uri": uri,
                "address": address,
                "format": "base64"
            }
            if amount is not None:
                response_data["amount"] = amount
            if memo:
                response_data["memo"] = memo
            if expires_at is not None:
                response_data["expires_at"] = expires_at

            return jsonify(response_data), 200

    except Exception as e:
        logger.error(
            "Payment QR generation failed",
            extra={
                "address": address,
                "amount": amount,
                "error": str(e),
                "event": "payment_qr.generation_failed"
            }
        )
        return jsonify({
            "error": "QR generation failed",
            "detail": str(e),
            "code": "qr_generation_error"
        }), 500

@payment_bp.route("/request", methods=["POST"])
def create_payment_request() -> tuple[Response, int]:
    """Create a tracked payment request with QR code.

    This endpoint creates a payment request that can be tracked and verified.
    It generates a unique request ID and stores the request details.

    Request Body (JSON):
        {
            "address": "XAI1...",           # Required: recipient address
            "amount": "100.50",             # Required: payment amount
            "memo": "Invoice #123",         # Optional: payment memo
            "expiry_minutes": 30,           # Optional: expiry time (default: 60)
            "callback_url": "https://..."   # Optional: webhook URL for payment notification
        }

    Returns:
        JSON response (201 Created) with payment request details

    Raises:
        400: If request data is invalid
        500: If creation fails
    """
    if not QRCODE_AVAILABLE:
        return jsonify({
            "error": "QR code generation not available",
            "detail": "qrcode library not installed",
            "code": "qrcode_unavailable"
        }), 400

    data = request.get_json()
    if not data:
        return jsonify({
            "error": "Invalid request",
            "detail": "JSON body required",
            "code": "invalid_request"
        }), 400

    # Validate required fields
    address = data.get("address")
    amount = data.get("amount")

    if not address:
        return jsonify({
            "error": "Missing required field",
            "detail": "address is required",
            "code": "missing_address"
        }), 400

    if amount is None:
        return jsonify({
            "error": "Missing required field",
            "detail": "amount is required for payment requests",
            "code": "missing_amount"
        }), 400

    try:
        validate_address(address)
    except ValueError as e:
        return jsonify({
            "error": "Invalid address",
            "detail": str(e),
            "code": "invalid_address"
        }), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({
                "error": "Invalid amount",
                "detail": "Amount must be positive",
                "code": "invalid_amount"
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "error": "Invalid amount",
            "detail": "Amount must be a valid number",
            "code": "invalid_amount"
        }), 400

    # Extract optional fields
    memo = data.get("memo", "")
    expiry_minutes = data.get("expiry_minutes", 60)
    callback_url = data.get("callback_url")

    # Validate memo
    if memo and len(memo) > 1000:
        return jsonify({
            "error": "Invalid memo",
            "detail": "Memo exceeds 1000 characters",
            "code": "memo_too_long"
        }), 400

    # Validate expiry
    try:
        expiry_minutes = int(expiry_minutes)
        if expiry_minutes <= 0:
            return jsonify({
                "error": "Invalid expiry",
                "detail": "Expiry must be positive",
                "code": "invalid_expiry"
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "error": "Invalid expiry",
            "detail": "Expiry must be a valid integer",
            "code": "invalid_expiry"
        }), 400

    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        created_at = int(time.time())
        expires_at = created_at + (expiry_minutes * 60)

        # Generate payment QR code
        qr_data = TransactionQRGenerator.generate_payment_request_qr(
            address=address,
            amount=amount,
            label=None,
            message=memo if memo else None,
            return_format="base64"
        )

        # Build payment URI
        uri = f"xai:{address}?amount={amount}"
        if memo:
            uri += f"&memo={quote(memo)}"
        uri += f"&exp={expires_at}"

        # Store payment request
        _payment_requests[request_id] = {
            "request_id": request_id,
            "address": address,
            "amount": amount,
            "memo": memo,
            "expires_at": expires_at,
            "created_at": created_at,
            "status": "pending",  # pending, paid, expired, cancelled
            "callback_url": callback_url,
            "paid_txid": None,
            "paid_at": None,
        }

        # Return payment request details
        return jsonify({
            "request_id": request_id,
            "qr_code": qr_data,
            "uri": uri,
            "address": address,
            "amount": amount,
            "memo": memo,
            "expires_at": expires_at,
            "created_at": created_at,
            "status": "pending",
        }), 201

    except Exception as e:
        logger.error(
            "Payment request creation failed",
            extra={
                "address": address,
                "amount": amount,
                "error": str(e),
                "event": "payment_request.creation_failed"
            }
        )
        return jsonify({
            "error": "Payment request creation failed",
            "detail": str(e),
            "code": "creation_error"
        }), 500

@payment_bp.route("/request/<request_id>", methods=["GET"])
def get_payment_request(request_id: str) -> tuple[Response, int]:
    """Get payment request details and check status.

    This endpoint retrieves a payment request by ID and checks if payment
    has been received. It automatically updates status based on blockchain
    state and expiry time.

    Path Parameters:
        request_id (str): UUID of the payment request

    Returns:
        JSON response (200 OK) with payment request status

    Raises:
        404: If request_id not found
        500: If status check fails
    """
    # Lookup payment request
    payment_request = _payment_requests.get(request_id)
    if not payment_request:
        return jsonify({
            "error": "Payment request not found",
            "detail": f"No payment request with ID: {request_id}",
            "code": "request_not_found"
        }), 404

    try:
        blockchain = get_blockchain()

        # Check if expired
        current_time = int(time.time())
        if payment_request["status"] == "pending" and current_time > payment_request["expires_at"]:
            payment_request["status"] = "expired"
            _payment_requests[request_id] = payment_request

        # Check for payment on blockchain (if still pending)
        if payment_request["status"] == "pending":
            # Get recent transactions to the address
            address = payment_request["address"]
            expected_amount = payment_request["amount"]

            # Search recent blocks for payment
            # In production, this should use an index or transaction history
            recent_blocks = blockchain.chain[-100:]  # Check last 100 blocks
            for block in recent_blocks:
                for tx in block.transactions:
                    if (tx.recipient == address and
                        tx.amount >= expected_amount and
                        tx.timestamp >= payment_request["created_at"]):
                        # Payment found
                        payment_request["status"] = "paid"
                        payment_request["paid_txid"] = tx.txid
                        payment_request["paid_at"] = tx.timestamp
                        _payment_requests[request_id] = payment_request
                        break
                if payment_request["status"] == "paid":
                    break

        # Return payment request status
        response_data = {
            "request_id": payment_request["request_id"],
            "address": payment_request["address"],
            "amount": payment_request["amount"],
            "memo": payment_request["memo"],
            "expires_at": payment_request["expires_at"],
            "created_at": payment_request["created_at"],
            "status": payment_request["status"],
        }

        if payment_request["paid_txid"]:
            response_data["paid_txid"] = payment_request["paid_txid"]
            response_data["paid_at"] = payment_request["paid_at"]

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(
            "Payment request status check failed",
            extra={
                "request_id": request_id,
                "error": str(e),
                "event": "payment_request.status_check_failed"
            }
        )
        return jsonify({
            "error": "Status check failed",
            "detail": str(e),
            "code": "status_check_error"
        }), 500

@payment_bp.route("/parse", methods=["POST"])
def parse_payment_uri() -> tuple[Response, int]:
    """Parse a payment URI from QR code scan.

    This endpoint accepts a payment URI (typically scanned from QR code)
    and parses it into structured data for display and validation.

    Request Body (JSON):
        {
            "uri": "xai:address?amount=100.50&memo=Invoice%20123&exp=1703001234"
        }

    Returns:
        JSON response (200 OK) with parsed payment data

    Raises:
        400: If URI is invalid or missing
        500: If parsing fails
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "error": "Invalid request",
            "detail": "JSON body required",
            "code": "invalid_request"
        }), 400

    uri = data.get("uri")
    if not uri:
        return jsonify({
            "error": "Missing required field",
            "detail": "uri is required",
            "code": "missing_uri"
        }), 400

    try:
        # Parse the payment URI
        parsed = TransactionQRGenerator.parse_payment_uri(uri)

        # Validate the parsed data
        is_valid = QRCodeValidator.validate_payment_uri(uri)

        # Check expiry if present
        is_expired = False
        expires_at = None
        if "exp" in uri:
            # Extract expiry from URI parameters
            if "?" in uri:
                params_str = uri.split("?", 1)[1]
                params = dict(param.split("=", 1) for param in params_str.split("&") if "=" in param)
                if "exp" in params:
                    try:
                        expires_at = int(params["exp"])
                        is_expired = int(time.time()) > expires_at
                    except (ValueError, TypeError):
                        pass

        # Build response
        response_data = {
            "address": parsed.get("address"),
            "valid": is_valid,
            "expired": is_expired,
        }

        if "amount" in parsed:
            response_data["amount"] = parsed["amount"]
        if "message" in parsed:
            # URL decode the message
            response_data["memo"] = unquote(parsed["message"])
        elif "label" in parsed:
            response_data["memo"] = unquote(parsed["label"])
        if expires_at is not None:
            response_data["expires_at"] = expires_at

        return jsonify(response_data), 200

    except ValueError as e:
        return jsonify({
            "error": "Invalid payment URI",
            "detail": str(e),
            "code": "invalid_uri"
        }), 400
    except Exception as e:
        logger.error(
            "Payment URI parsing failed",
            extra={
                "uri": uri,
                "error": str(e),
                "event": "payment_uri.parse_failed"
            }
        )
        return jsonify({
            "error": "URI parsing failed",
            "detail": str(e),
            "code": "parse_error"
        }), 500

@payment_bp.route("/verify", methods=["POST"])
def verify_payment() -> tuple[Response, int]:
    """Verify a payment against a payment request.

    This endpoint verifies that a payment transaction matches a payment request,
    checking amount, recipient, and expiry status. Used by merchants to validate
    received payments.

    Request Body (JSON):
        {
            "request_id": "uuid",           # Optional: Payment request ID
            "txid": "tx123...",             # Required: Transaction ID
            "sender": "XAI1...",            # Required: Sender address
            "recipient": "XAI2...",         # Required: Recipient address
            "amount": 100.50,               # Required: Transaction amount
            "timestamp": 1703001234,        # Required: Transaction timestamp
            "confirmations": 6              # Optional: Number of confirmations
        }

    Returns:
        JSON response (200 OK) with verification result

    Raises:
        400: If request data is invalid
        404: If payment request not found
        500: If verification fails
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "error": "Invalid request",
            "detail": "JSON body required",
            "code": "invalid_request"
        }), 400

    # Extract required fields
    txid = data.get("txid")
    recipient = data.get("recipient")
    amount = data.get("amount")
    timestamp = data.get("timestamp")

    # Validate required fields
    if not txid:
        return jsonify({
            "error": "Missing required field",
            "detail": "txid is required",
            "code": "missing_txid"
        }), 400

    if not recipient:
        return jsonify({
            "error": "Missing required field",
            "detail": "recipient is required",
            "code": "missing_recipient"
        }), 400

    if amount is None:
        return jsonify({
            "error": "Missing required field",
            "detail": "amount is required",
            "code": "missing_amount"
        }), 400

    # Validate recipient address
    try:
        validate_address(recipient)
    except ValueError as e:
        return jsonify({
            "error": "Invalid recipient address",
            "detail": str(e),
            "code": "invalid_recipient"
        }), 400

    # Extract optional fields
    request_id = data.get("request_id")
    confirmations = data.get("confirmations", 0)

    try:
        blockchain = get_blockchain()

        # If request_id provided, verify against payment request
        if request_id:
            payment_request = _payment_requests.get(request_id)

            if not payment_request:
                return jsonify({
                    "error": "Payment request not found",
                    "detail": f"No payment request with ID: {request_id}",
                    "code": "request_not_found"
                }), 404

            # Check if expired
            current_time = int(time.time())
            if payment_request["expires_at"] and current_time > payment_request["expires_at"]:
                return jsonify({
                    "valid": False,
                    "verified": False,
                    "error": "Payment request expired",
                    "error_code": "request_expired",
                    "expires_at": payment_request["expires_at"],
                    "current_time": current_time
                }), 200

            # Verify amount
            expected_amount = payment_request["amount"]
            if abs(float(amount) - expected_amount) > 0.000001:
                return jsonify({
                    "valid": False,
                    "verified": False,
                    "error": "Amount mismatch",
                    "error_code": "amount_mismatch",
                    "expected": expected_amount,
                    "received": float(amount)
                }), 200

            # Verify recipient
            if recipient != payment_request["address"]:
                return jsonify({
                    "valid": False,
                    "verified": False,
                    "error": "Recipient mismatch",
                    "error_code": "recipient_mismatch",
                    "expected": payment_request["address"],
                    "received": recipient
                }), 200

            # Verify timestamp is after request creation
            if timestamp and timestamp < payment_request["created_at"]:
                return jsonify({
                    "valid": False,
                    "verified": False,
                    "error": "Transaction predates payment request",
                    "error_code": "invalid_timestamp",
                    "request_created": payment_request["created_at"],
                    "transaction_time": timestamp
                }), 200

            # Update payment request status
            if payment_request["status"] == "pending":
                payment_request["status"] = "paid"
                payment_request["paid_txid"] = txid
                payment_request["paid_at"] = timestamp or current_time
                _payment_requests[request_id] = payment_request

            # Payment verified successfully
            return jsonify({
                "valid": True,
                "verified": True,
                "request_id": request_id,
                "txid": txid,
                "amount": float(amount),
                "recipient": recipient,
                "confirmations": confirmations,
                "status": payment_request["status"],
                "message": "Payment verified successfully"
            }), 200

        else:
            # No request_id - just validate transaction structure
            # Search blockchain for transaction
            found = False
            for block in blockchain.chain[-100:]:  # Check last 100 blocks
                for tx in block.transactions:
                    if tx.txid == txid:
                        found = True
                        # Verify transaction details
                        if tx.recipient != recipient:
                            return jsonify({
                                "valid": False,
                                "verified": False,
                                "error": "Recipient mismatch",
                                "error_code": "recipient_mismatch",
                                "expected_from_chain": tx.recipient,
                                "provided": recipient
                            }), 200

                        if abs(tx.amount - float(amount)) > 0.000001:
                            return jsonify({
                                "valid": False,
                                "verified": False,
                                "error": "Amount mismatch",
                                "error_code": "amount_mismatch",
                                "expected_from_chain": tx.amount,
                                "provided": float(amount)
                            }), 200

                        # Transaction verified on blockchain
                        return jsonify({
                            "valid": True,
                            "verified": True,
                            "txid": txid,
                            "amount": tx.amount,
                            "recipient": tx.recipient,
                            "sender": tx.sender,
                            "confirmations": confirmations,
                            "on_chain": True,
                            "message": "Transaction verified on blockchain"
                        }), 200

            if not found:
                return jsonify({
                    "valid": False,
                    "verified": False,
                    "error": "Transaction not found on blockchain",
                    "error_code": "tx_not_found",
                    "txid": txid
                }), 200

    except Exception as e:
        logger.error(
            "Payment verification failed",
            extra={
                "txid": txid,
                "recipient": recipient,
                "amount": amount,
                "error": str(e),
                "event": "payment.verification_failed"
            }
        )
        return jsonify({
            "error": "Verification failed",
            "detail": str(e),
            "code": "verification_error"
        }), 500
