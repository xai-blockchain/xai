from __future__ import annotations

"""
XAI Blockchain - Security Validation Module

Comprehensive input validation and sanitization.
Protects against:
- Injection attacks
- Integer overflow/underflow
- Invalid addresses
- Negative amounts
- Excessive fees
- Malformed data
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable

# Security logger setup
security_logger = logging.getLogger("xai.security")
security_logger.setLevel(logging.INFO)

# Create handler if not exists
if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - SECURITY - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

class SecurityEventRouter:
    """Dispatches security events to registered sinks (metrics, alerting, etc.)."""

    _sinks: list[Callable[[str, dict[str, Any], str], None]] = []

    @classmethod
    def register_sink(cls, sink: Callable[[str, dict[str, Any], str], None]) -> None:
        """Register a callable sink to receive security events."""
        if sink and sink not in cls._sinks:
            cls._sinks.append(sink)

    @classmethod
    def dispatch(cls, event_type: str, details: dict[str, Any], severity: str) -> None:
        """
        Dispatch a security event to all registered sinks unless disabled via env.
        """
        if os.getenv("XAI_P2P_DISABLE_SECURITY_EVENTS", "0").lower() in {"1", "true", "yes", "on"}:
            return
        for sink in list(cls._sinks):
            try:
                sink(event_type, details, severity)
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                security_logger.debug(
                    "SecurityEventRouter sink failure: %s", exc, exc_info=True
                )

def log_security_event(event_type: str, details: dict[str, Any], severity: str = "INFO"):
    """
    Log security-related events in structured format

    Args:
        event_type: Type of security event (e.g., 'validation_failure', 'injection_attempt')
        details: Dictionary with event details
        severity: Log level (INFO, WARNING, ERROR, CRITICAL)
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": details,
    }

    log_message = json.dumps(log_entry)

    if severity == "CRITICAL":
        security_logger.critical(log_message)
    elif severity == "ERROR":
        security_logger.error(log_message)
    elif severity == "WARNING":
        security_logger.warning(log_message)
    else:
        security_logger.info(log_message)

    SecurityEventRouter.dispatch(event_type, details, severity)

class ValidationError(Exception):
    """Validation error - safe to expose to users"""

    pass

class SecurityValidator:
    """
    Security validation for all user inputs

    All validation errors are safe to display to users.
    No internal information leaked.
    """

    # Constants
    MAX_SUPPLY = 121000000.0
    MAX_TRANSACTION_AMOUNT = MAX_SUPPLY
    MAX_FEE = 1000.0  # Prevent excessive fees
    MIN_AMOUNT = 0.00000001  # 1 satoshi equivalent

    # Address validation
    VALID_PREFIXES = ["XAI", "XAI", "TXAI"]
    MIN_ADDRESS_LENGTH = 40
    MAX_ADDRESS_LENGTH = 100

    # String limits (prevent memory exhaustion)
    MAX_STRING_LENGTH = 1000
    MAX_JSON_SIZE = 1024 * 1024  # 1MB

    @staticmethod
    def validate_amount(amount: Any, field_name: str = "amount") -> float:
        """
        Validate transaction amount using centralized validation.

        Args:
            amount: Amount to validate
            field_name: Name of field (for error messages)

        Returns:
            float: Validated amount

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.validation import validate_amount as core_validate_amount

        try:
            return core_validate_amount(
                amount,
                allow_zero=False,
                min_value=SecurityValidator.MIN_AMOUNT,
                max_value=SecurityValidator.MAX_TRANSACTION_AMOUNT
            )
        except ValueError as e:
            raise ValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def validate_address(address: Any, field_name: str = "address") -> str:
        """
        Validate XAI blockchain address using centralized validation with security checks.

        Args:
            address: Address to validate
            field_name: Name of field

        Returns:
            str: Validated address

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.config import NETWORK
        from xai.core.validation import AddressFormatValidator

        # Type check
        if not isinstance(address, str):
            raise ValidationError(f"{field_name} must be a string")

        address = address.strip()
        if not address:
            raise ValidationError(f"{field_name} cannot be empty")

        # SECURITY ENHANCEMENT: Injection pattern detection
        dangerous_patterns = [
            (r"['\";<>&|`$(){}]", "sql_injection_chars"),  # SQL injection, command injection chars
            (r"<script", "xss_attempt"),  # XSS attempts
            (r"javascript:", "javascript_protocol"),  # JavaScript protocol
            (r"\.\.\/", "path_traversal"),  # Path traversal
            (r"\\x[0-9a-fA-F]{2}", "hex_escape"),  # Hex escape sequences
            (r"%[0-9a-fA-F]{2}", "url_encoding"),  # URL encoding
        ]

        for pattern, attack_type in dangerous_patterns:
            if re.search(pattern, address, re.IGNORECASE):
                # Log security event
                log_security_event(
                    "injection_attempt_detected",
                    {
                        "field": field_name,
                        "attack_type": attack_type,
                        "input_length": len(address),
                        "pattern_matched": pattern,
                    },
                    severity="WARNING",
                )
                raise ValidationError(f"{field_name} contains invalid or dangerous characters")

        # Use centralized validation with network-aware prefix enforcement
        try:
            expected_prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
            validator = AddressFormatValidator(
                expected_prefix=expected_prefix,
                allow_special=True,
                allow_legacy=True,
            )
            return validator.validate(address)
        except ValueError as e:
            raise ValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def validate_fee(fee: Any) -> float:
        """
        Validate transaction fee using centralized validation.

        Args:
            fee: Fee to validate

        Returns:
            float: Validated fee

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.validation import validate_fee as core_validate_fee

        try:
            return core_validate_fee(fee)
        except ValueError as e:
            raise ValidationError(f"fee: {e}") from e

    @staticmethod
    def validate_string(value: Any, field_name: str = "value", max_length: int = None) -> str:
        """
        Validate and sanitize string input using centralized validation.

        Args:
            value: String to validate
            field_name: Name of field
            max_length: Maximum allowed length

        Returns:
            str: Sanitized string

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.validation import validate_string as core_validate_string

        try:
            max_len = max_length or SecurityValidator.MAX_STRING_LENGTH
            return core_validate_string(value, max_length=max_len, allow_empty=False)
        except ValueError as e:
            raise ValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def validate_positive_integer(value: Any, field_name: str = "value") -> int:
        """
        Validate positive integer using centralized validation.

        Args:
            value: Value to validate
            field_name: Name of field

        Returns:
            int: Validated integer

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.validation import validate_positive_integer as core_validate_positive_integer

        try:
            return core_validate_positive_integer(value, min_value=0, max_value=2**63 - 1)
        except ValueError as e:
            raise ValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def validate_timestamp(timestamp: Any, field_name: str = "timestamp") -> float:
        """
        Validate UTC timestamp

        Args:
            timestamp: Timestamp to validate
            field_name: Name of field

        Returns:
            float: Validated timestamp

        Raises:
            ValidationError: If validation fails
        """
        # Type check
        if not isinstance(timestamp, (int, float)):
            raise ValidationError(f"{field_name} must be a number")

        try:
            timestamp = float(timestamp)
        except (ValueError, OverflowError):
            raise ValidationError(f"Invalid {field_name}")

        # Reasonable range (after year 2000, before year 2100)
        if timestamp < 946684800:  # 2000-01-01
            raise ValidationError(f"{field_name} is too old")

        if timestamp > 4102444800:  # 2100-01-01
            raise ValidationError(f"{field_name} is too far in future")

        # Not too far in future (allow 2 hour clock drift)
        current_time = datetime.now(timezone.utc).timestamp()
        if timestamp > current_time + 7200:
            raise ValidationError(f"{field_name} is too far in future")

        return timestamp

    @staticmethod
    def validate_hex_string(value: Any, field_name: str = "value", exact_length: int = None) -> str:
        """
        Validate hexadecimal string using centralized validation.

        Args:
            value: Hex string to validate
            field_name: Name of field
            exact_length: Exact length required (optional)

        Returns:
            str: Validated hex string

        Raises:
            ValidationError: If validation fails
        """
        from xai.core.validation import validate_hex_string as core_validate_hex_string

        try:
            return core_validate_hex_string(value, exact_length=exact_length)
        except ValueError as e:
            raise ValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def validate_network_type(network: Any) -> str:
        """
        Validate network type

        Args:
            network: Network to validate

        Returns:
            str: Validated network ('testnet' or 'mainnet')

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(network, str):
            raise ValidationError("Network must be a string")

        network = network.lower().strip()

        if network not in ["testnet", "mainnet"]:
            raise ValidationError("Network must be 'testnet' or 'mainnet'")

        return network

    @staticmethod
    def sanitize_for_logging(data: Any) -> str:
        """
        Sanitize data for logging

        Args:
            data: Data to sanitize

        Returns:
            str: Sanitized string safe for logging
        """
        if isinstance(data, dict):
            # Remove sensitive keys
            sensitive_keys = ["ip", "ip_address", "user", "email", "phone", "location", "geo"]
            sanitized = {k: v for k, v in data.items() if k.lower() not in sensitive_keys}

            # Truncate addresses for privacy
            if "address" in sanitized and isinstance(sanitized["address"], str):
                addr = sanitized["address"]
                if len(addr) > 20:
                    sanitized["address"] = f"{addr[:10]}...{addr[-6:]}"

            return str(sanitized)

        elif isinstance(data, str):
            # Truncate long strings
            if len(data) > 100:
                return f"{data[:50]}...(truncated)"
            return data

        else:
            return str(data)

# Convenience functions for common validations

def validate_transaction_data(data: dict) -> dict:
    """
    Validate complete transaction data

    Args:
        data: Transaction data dictionary

    Returns:
        dict: Validated transaction data

    Raises:
        ValidationError: If validation fails
    """
    validator = SecurityValidator()

    # Required fields
    if "sender" not in data:
        raise ValidationError("Missing required field: sender")
    if "recipient" not in data:
        raise ValidationError("Missing required field: recipient")
    if "amount" not in data:
        raise ValidationError("Missing required field: amount")

    # Validate each field
    validated = {
        "sender": validator.validate_address(data["sender"], "sender"),
        "recipient": validator.validate_address(data["recipient"], "recipient"),
        "amount": validator.validate_amount(data["amount"], "amount"),
        "fee": validator.validate_fee(data.get("fee", 0.24)),
    }

    # Optional fields
    if "private_key" in data:
        validated["private_key"] = validator.validate_hex_string(
            data["private_key"], "private_key", exact_length=64
        )

    return validated

def validate_api_request(data: dict, max_size: int = SecurityValidator.MAX_JSON_SIZE) -> dict:
    """
    Validate API request data

    Args:
        data: Request data
        max_size: Maximum JSON size in bytes

    Returns:
        dict: Validated data

    Raises:
        ValidationError: If validation fails
    """
    # Size check
    import json

    json_str = json.dumps(data)
    if len(json_str) > max_size:
        raise ValidationError(f"Request too large (maximum: {max_size} bytes)")

    return data
