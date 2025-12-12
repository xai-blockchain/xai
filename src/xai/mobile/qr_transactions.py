"""
QR Code Generation for Transactions
Task 179: Implement QR code generation for transactions

This module provides QR code generation for easy transaction sharing
and mobile wallet integration.
"""

from __future__ import annotations

import json
import base64
import binascii
import logging
from typing import Dict, Any, Optional
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class TransactionQRGenerator:
    """Generate QR codes for transactions and payment requests"""

    @staticmethod
    def generate_payment_request_qr(
        address: str,
        amount: Optional[float] = None,
        label: Optional[str] = None,
        message: Optional[str] = None,
        return_format: str = "base64"
    ) -> str:
        """
        Generate QR code for payment request

        Args:
            address: Recipient address
            amount: Payment amount (optional)
            label: Label for the address (optional)
            message: Message for the payment (optional)
            return_format: 'base64' or 'bytes'

        Returns:
            QR code as base64 string or bytes
        """
        if not QRCODE_AVAILABLE:
            raise ImportError("qrcode library not installed. Install with: pip install qrcode[pil]")

        # Build payment URI (similar to Bitcoin BIP21)
        uri = f"xai:{address}"
        params = []

        if amount is not None:
            params.append(f"amount={amount}")
        if label:
            params.append(f"label={label}")
        if message:
            params.append(f"message={message}")

        if params:
            uri += "?" + "&".join(params)

        return TransactionQRGenerator._generate_qr_code(uri, return_format)

    @staticmethod
    def generate_transaction_qr(transaction_data: Dict[str, Any], return_format: str = "base64") -> str:
        """
        Generate QR code for a signed transaction

        Args:
            transaction_data: Transaction dictionary
            return_format: 'base64' or 'bytes'

        Returns:
            QR code as base64 string or bytes
        """
        if not QRCODE_AVAILABLE:
            raise ImportError("qrcode library not installed. Install with: pip install qrcode[pil]")

        # Serialize transaction
        tx_json = json.dumps(transaction_data, sort_keys=True)

        # For large transactions, use base64 encoding
        if len(tx_json) > 500:
            tx_data = base64.b64encode(tx_json.encode()).decode()
            data = f"xai:tx:{tx_data}"
        else:
            data = f"xai:tx:{tx_json}"

        return TransactionQRGenerator._generate_qr_code(data, return_format)

    @staticmethod
    def generate_address_qr(address: str, return_format: str = "base64") -> str:
        """
        Generate simple QR code for an address

        Args:
            address: Wallet address
            return_format: 'base64' or 'bytes'

        Returns:
            QR code as base64 string or bytes
        """
        if not QRCODE_AVAILABLE:
            raise ImportError("qrcode library not installed. Install with: pip install qrcode[pil]")

        return TransactionQRGenerator._generate_qr_code(f"xai:{address}", return_format)

    @staticmethod
    def _generate_qr_code(data: str, return_format: str = "base64") -> str:
        """
        Internal method to generate QR code

        Args:
            data: Data to encode
            return_format: 'base64' or 'bytes'

        Returns:
            QR code as specified format
        """
        # Create QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_bytes = buffer.getvalue()

        if return_format == "base64":
            return base64.b64encode(qr_bytes).decode()
        else:
            return qr_bytes

    @staticmethod
    def parse_payment_uri(uri: str) -> Dict[str, Any]:
        """
        Parse a payment URI from QR code

        Args:
            uri: Payment URI string

        Returns:
            Dictionary with address and optional parameters
        """
        if not uri.startswith("xai:"):
            raise ValueError("Invalid XAI payment URI")

        uri = uri[4:]  # Remove 'xai:' prefix

        # Split address and parameters
        if "?" in uri:
            address, params_str = uri.split("?", 1)
            params = dict(param.split("=", 1) for param in params_str.split("&"))
        else:
            address = uri
            params = {}

        result = {"address": address}

        # Parse amount if present
        if "amount" in params:
            try:
                result["amount"] = float(params["amount"])
            except ValueError as e:
                # Invalid amount format - skip it
                logger.debug(
                    "Invalid amount in payment request QR code",
                    extra={"error": str(e), "amount": params["amount"], "event": "qr.invalid_amount"}
                )

        # Add label and message
        if "label" in params:
            result["label"] = params["label"]
        if "message" in params:
            result["message"] = params["message"]

        return result

    @staticmethod
    def parse_transaction_qr(qr_data: str) -> Dict[str, Any]:
        """
        Parse transaction data from QR code

        Args:
            qr_data: QR code data string

        Returns:
            Transaction dictionary
        """
        if not qr_data.startswith("xai:tx:"):
            raise ValueError("Invalid XAI transaction QR code")

        tx_data = qr_data[7:]  # Remove 'xai:tx:' prefix

        # Try to decode as base64 first
        try:
            decoded = base64.b64decode(tx_data).decode()
            return json.loads(decoded)
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
            # Direct JSON fallback
            logger.debug("Base64 decode failed, trying direct JSON: %s", e)
            return json.loads(tx_data)


class MobilePaymentEncoder:
    """Encode payment information for mobile wallets"""

    @staticmethod
    def create_payment_link(
        address: str,
        amount: Optional[float] = None,
        memo: Optional[str] = None
    ) -> str:
        """
        Create a payment deep link for mobile apps

        Args:
            address: Recipient address
            amount: Payment amount
            memo: Payment memo

        Returns:
            Deep link URL
        """
        link = f"xai://pay/{address}"
        params = []

        if amount is not None:
            params.append(f"amount={amount}")
        if memo:
            params.append(f"memo={memo}")

        if params:
            link += "?" + "&".join(params)

        return link

    @staticmethod
    def create_transaction_share_data(tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create shareable transaction data for mobile

        Args:
            tx_data: Transaction data

        Returns:
            Formatted share data with QR code
        """
        qr_generator = TransactionQRGenerator()

        share_data = {
            "txid": tx_data.get("txid"),
            "sender": tx_data.get("sender"),
            "recipient": tx_data.get("recipient"),
            "amount": tx_data.get("amount"),
            "timestamp": tx_data.get("timestamp"),
            "qr_code": qr_generator.generate_transaction_qr(tx_data) if QRCODE_AVAILABLE else None,
            "deep_link": MobilePaymentEncoder.create_payment_link(
                tx_data.get("recipient", ""),
                tx_data.get("amount")
            )
        }

        return share_data


class QRCodeValidator:
    """Validate QR code data for security"""

    @staticmethod
    def validate_payment_uri(uri: str) -> bool:
        """
        Validate payment URI format

        Args:
            uri: Payment URI to validate

        Returns:
            True if valid
        """
        try:
            parsed = TransactionQRGenerator.parse_payment_uri(uri)

            # Validate address format
            if not parsed.get("address", "").startswith("XAI"):
                return False

            # Validate amount if present
            if "amount" in parsed:
                amount = parsed["amount"]
                if not isinstance(amount, (int, float)) or amount <= 0:
                    return False

            return True
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug("Payment link validation failed: %s", e)
            return False

    @staticmethod
    def validate_transaction_qr(qr_data: str) -> bool:
        """
        Validate transaction QR code data

        Args:
            qr_data: QR code data

        Returns:
            True if valid
        """
        try:
            tx_data = TransactionQRGenerator.parse_transaction_qr(qr_data)

            # Basic validation
            required_fields = ["txid", "sender", "recipient", "amount"]
            for field in required_fields:
                if field not in tx_data:
                    return False

            # Validate addresses
            if not tx_data["sender"].startswith("XAI") and tx_data["sender"] != "COINBASE":
                return False
            if not tx_data["recipient"].startswith("XAI"):
                return False

            # Validate amount
            if not isinstance(tx_data["amount"], (int, float)) or tx_data["amount"] < 0:
                return False

            return True
        except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as e:
            logger.debug("Transaction QR validation failed: %s", e)
            return False

    @staticmethod
    def sanitize_qr_data(data: str, max_length: int = 4096) -> str:
        """
        Sanitize QR code data to prevent attacks

        Args:
            data: QR code data
            max_length: Maximum allowed length

        Returns:
            Sanitized data

        Raises:
            ValueError: If data is invalid
        """
        if not isinstance(data, str):
            raise ValueError("QR data must be a string")

        if len(data) > max_length:
            raise ValueError(f"QR data exceeds maximum length of {max_length}")

        # Remove null bytes and control characters
        sanitized = "".join(c for c in data if c.isprintable() or c in "\n\r\t")

        return sanitized
