"""Payment QR code generation API routes.

This module provides REST API endpoints for generating QR codes for payment addresses
and payment requests with amounts, memos, and expiry times.

Endpoints:
- GET /payment/qr/<address> - Generate simple address QR code (PNG image)
- POST /payment/qr - Generate payment request QR with amount, memo, expiry
"""

from __future__ import annotations

import logging
import time
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.parse import quote

from flask import Response, jsonify, request, send_file

from xai.core.validation import validate_address
from xai.mobile.qr_transactions import (
    QRCODE_AVAILABLE,
    TransactionQRGenerator,
)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_payment_qr_routes(routes: "NodeAPIRoutes") -> None:
    """Register payment QR code generation routes.

    Args:
        routes: NodeAPIRoutes instance containing app and blockchain references
    """
    app = routes.app

    @app.route("/payment/qr/<address>", methods=["GET"])
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

    @app.route("/payment/qr", methods=["POST"])
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
            If format='base64': JSON with:
                {
                    "qr_code": "<base64_string>",
                    "uri": "xai:address?amount=100.50&memo=...",
                    "address": "XAI1...",
                    "amount": 100.50,
                    "memo": "Invoice #123",
                    "expires_at": 1703001234,    # Unix timestamp (if expiry set)
                    "format": "base64"
                }

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
