"""
Comprehensive tests for security_validation.py to achieve 100% coverage

Tests all validation functions, edge cases, sanitization, and security features
"""

import pytest
import time
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet
from xai.core.security_validation import (
    SecurityValidator,
    ValidationError,
    validate_transaction_data,
    validate_api_request,
    log_security_event,
    SecurityEventRouter,
)
from xai.core.node import BlockchainNode
from xai.core.security_webhook_forwarder import SecurityWebhookForwarder as _SecurityWebhookForwarder


class TestSecurityValidatorConstants:
    """Test SecurityValidator constants"""

    def test_constants_are_defined(self):
        """Test all security constants are properly defined"""
        assert SecurityValidator.MAX_SUPPLY == 121000000.0
        assert SecurityValidator.MAX_TRANSACTION_AMOUNT == SecurityValidator.MAX_SUPPLY
        assert SecurityValidator.MAX_FEE == 1000.0
        assert SecurityValidator.MIN_AMOUNT == 0.00000001

        assert "XAI" in SecurityValidator.VALID_PREFIXES
        assert "XAI" in SecurityValidator.VALID_PREFIXES
        assert "TXAI" in SecurityValidator.VALID_PREFIXES

        assert SecurityValidator.MIN_ADDRESS_LENGTH == 40
        assert SecurityValidator.MAX_ADDRESS_LENGTH == 100
        assert SecurityValidator.MAX_STRING_LENGTH == 1000
        assert SecurityValidator.MAX_JSON_SIZE == 1024 * 1024


class TestAmountValidation:
    """Test validate_amount function"""

    def test_validate_valid_amount(self):
        """Test validating a valid amount"""
        amount = SecurityValidator.validate_amount(10.5)
        assert amount == 10.5

    def test_validate_amount_integer(self):
        """Test validating integer amount"""
        amount = SecurityValidator.validate_amount(10)
        assert amount == 10.0

    def test_validate_amount_not_number(self):
        """Test rejecting non-number amount"""
        with pytest.raises(ValidationError, match="must be numeric"):
            SecurityValidator.validate_amount("not_a_number")

    def test_validate_amount_nan(self):
        """Test rejecting NaN amount"""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            SecurityValidator.validate_amount(float('nan'))

    def test_validate_amount_positive_infinity(self):
        """Test rejecting positive infinity"""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            SecurityValidator.validate_amount(float('inf'))

    def test_validate_amount_negative_infinity(self):
        """Test rejecting negative infinity"""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            SecurityValidator.validate_amount(float('-inf'))

    def test_validate_amount_negative(self):
        """Test rejecting negative amount"""
        with pytest.raises(ValidationError, match="cannot be negative"):
            SecurityValidator.validate_amount(-10.0)

    def test_validate_amount_zero(self):
        """Test rejecting zero amount"""
        with pytest.raises(ValidationError, match="cannot be zero"):
            SecurityValidator.validate_amount(0.0)

    def test_validate_amount_too_small(self):
        """Test rejecting amount below minimum"""
        with pytest.raises(ValidationError, match="too small"):
            SecurityValidator.validate_amount(0.000000001)

    def test_validate_amount_too_large(self):
        """Test rejecting amount above maximum"""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            SecurityValidator.validate_amount(SecurityValidator.MAX_TRANSACTION_AMOUNT + 1)

    def test_validate_amount_precision(self):
        """Test amount is rounded to 8 decimal places"""
        amount = SecurityValidator.validate_amount(10.123456789)
        assert amount == 10.12345679

    def test_validate_amount_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="transaction_amount"):
            SecurityValidator.validate_amount(-1, "transaction_amount")


class TestAddressValidation:
    """Test validate_address function"""

    def test_validate_valid_xai_address(self):
        """Test validating valid XAI address"""
        address = "XAI" + "a" * 40
        result = SecurityValidator.validate_address(address)
        assert result == address

    def test_validate_valid_xai_address(self):
        """Test validating valid XAI address"""
        address = "XAI" + "b" * 40
        result = SecurityValidator.validate_address(address)
        assert result == address

    def test_validate_valid_txai_address(self):
        """Test validating valid TXAI address"""
        address = "TXAI" + "c" * 40
        result = SecurityValidator.validate_address(address)
        assert result == address

    def test_validate_coinbase_address(self):
        """Test COINBASE is accepted as special address"""
        address = SecurityValidator.validate_address("COINBASE")
        assert address == "COINBASE"

    def test_validate_address_not_string(self):
        """Test rejecting non-string address"""
        with pytest.raises(ValidationError, match="must be a string"):
            SecurityValidator.validate_address(12345)

    def test_validate_address_empty(self):
        """Test rejecting empty address"""
        with pytest.raises(ValidationError, match="cannot be empty"):
            SecurityValidator.validate_address("")

    def test_validate_address_whitespace_only(self):
        """Test rejecting whitespace-only address"""
        with pytest.raises(ValidationError, match="cannot be empty"):
            SecurityValidator.validate_address("   ")

    def test_validate_address_too_short(self):
        """Test rejecting address that is too short"""
        with pytest.raises(ValidationError, match="too short"):
            SecurityValidator.validate_address("XAI123")

    def test_validate_address_too_long(self):
        """Test rejecting address that is too long"""
        with pytest.raises(ValidationError, match="too long"):
            SecurityValidator.validate_address("XAI" + "a" * 200)

    def test_validate_address_invalid_prefix(self):
        """Test rejecting address with invalid prefix"""
        with pytest.raises(ValidationError, match="Invalid address prefix"):
            SecurityValidator.validate_address("INVALID" + "a" * 40)

    def test_validate_address_non_hex_characters(self):
        """Test rejecting address with non-hex characters"""
        with pytest.raises(ValidationError, match="Invalid address format"):
            SecurityValidator.validate_address("XAI" + "z" * 40)

    def test_validate_address_sql_injection(self):
        """Test detecting SQL injection attempts"""
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address("XAI" + "a" * 37 + "'; DROP TABLE users; --")

    def test_validate_address_xss_attempt(self):
        """Test detecting XSS attempts"""
        malicious = "XAI" + "a" * 37 + "<script>alert('xss')</script>"
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address(malicious)

    def test_validate_address_javascript_protocol(self):
        """Test detecting JavaScript protocol"""
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address("XAI" + "a" * 20 + "javascript:alert(1)")

    def test_validate_address_path_traversal(self):
        """Test detecting path traversal attempts"""
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address("XAI" + "a" * 20 + "../../../etc/passwd")

    def test_validate_address_hex_escape(self):
        """Test detecting hex escape sequences"""
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address("XAI" + "a" * 30 + "\\x41\\x42")

    def test_validate_address_url_encoding(self):
        """Test detecting URL encoding"""
        encoded = "XAI" + "a" * 34 + "%20%20"
        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            SecurityValidator.validate_address(encoded)

    def test_validate_address_strips_whitespace(self):
        """Test address whitespace is stripped"""
        address = SecurityValidator.validate_address("  XAI" + "a" * 40 + "  ")
        assert address == "XAI" + "a" * 40

    def test_validate_address_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="sender_address"):
            SecurityValidator.validate_address("", "sender_address")


class TestFeeValidation:
    """Test validate_fee function"""

    def test_validate_valid_fee(self):
        """Test validating valid fee"""
        fee = SecurityValidator.validate_fee(0.24)
        assert fee == 0.24

    def test_validate_zero_fee(self):
        """Test zero fee is allowed"""
        fee = SecurityValidator.validate_fee(0.0)
        assert fee == 0.0

    def test_validate_fee_not_number(self):
        """Test rejecting non-number fee"""
        with pytest.raises(ValidationError, match="must be numeric"):
            SecurityValidator.validate_fee("not_a_number")

    def test_validate_fee_nan(self):
        """Test rejecting NaN fee"""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            SecurityValidator.validate_fee(float('nan'))

    def test_validate_fee_positive_infinity(self):
        """Test rejecting positive infinity fee"""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            SecurityValidator.validate_fee(float('inf'))

    def test_validate_fee_negative_infinity(self):
        """Test rejecting negative infinity fee"""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            SecurityValidator.validate_fee(float('-inf'))

    def test_validate_fee_negative(self):
        """Test rejecting negative fee"""
        with pytest.raises(ValidationError, match="cannot be negative"):
            SecurityValidator.validate_fee(-1.0)

    def test_validate_fee_too_high(self):
        """Test rejecting fee that is too high"""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            SecurityValidator.validate_fee(SecurityValidator.MAX_FEE + 1)

    def test_validate_fee_precision(self):
        """Test fee is rounded to 8 decimal places"""
        fee = SecurityValidator.validate_fee(0.123456789)
        assert fee == 0.12345679


class TestStringValidation:
    """Test validate_string function"""

    def test_validate_valid_string(self):
        """Test validating valid string"""
        result = SecurityValidator.validate_string("Hello, World!")
        assert result == "Hello, World!"

    def test_validate_string_not_string(self):
        """Test rejecting non-string input"""
        with pytest.raises(ValidationError, match="must be a string"):
            SecurityValidator.validate_string(12345)

    def test_validate_string_too_long(self):
        """Test rejecting string that is too long"""
        long_string = "a" * (SecurityValidator.MAX_STRING_LENGTH + 1)
        with pytest.raises(ValidationError, match="too long"):
            SecurityValidator.validate_string(long_string)

    def test_validate_string_custom_max_length(self):
        """Test validating string with custom max length"""
        with pytest.raises(ValidationError, match="too long"):
            SecurityValidator.validate_string("a" * 101, max_length=100)

    def test_validate_string_control_characters(self):
        """Test rejecting string with control characters"""
        with pytest.raises(ValidationError, match="invalid control characters"):
            SecurityValidator.validate_string("test\x00string")

    def test_validate_string_allows_newlines(self):
        """Test newlines are allowed"""
        result = SecurityValidator.validate_string("line1\nline2")
        assert result == "line1\nline2"

    def test_validate_string_strips_whitespace(self):
        """Test whitespace is stripped"""
        result = SecurityValidator.validate_string("  test  ")
        assert result == "test"

    def test_validate_string_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="description"):
            SecurityValidator.validate_string(123, "description")


class TestPositiveIntegerValidation:
    """Test validate_positive_integer function"""

    def test_validate_valid_integer(self):
        """Test validating valid positive integer"""
        result = SecurityValidator.validate_positive_integer(42)
        assert result == 42

    def test_validate_integer_from_string(self):
        """Test converting string to integer"""
        result = SecurityValidator.validate_positive_integer("42")
        assert result == 42

    def test_validate_integer_not_convertible(self):
        """Test rejecting non-convertible value"""
        with pytest.raises(ValidationError, match="must be an integer"):
            SecurityValidator.validate_positive_integer("not_an_int")

    def test_validate_integer_negative(self):
        """Test rejecting negative integer"""
        with pytest.raises(ValidationError, match="must be >= 0"):
            SecurityValidator.validate_positive_integer(-1)

    def test_validate_integer_too_large(self):
        """Test rejecting integer that is too large"""
        with pytest.raises(ValidationError, match="must be <="):
            SecurityValidator.validate_positive_integer(2**63)

    def test_validate_integer_zero(self):
        """Test zero is considered positive"""
        result = SecurityValidator.validate_positive_integer(0)
        assert result == 0

    def test_validate_integer_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="block_height"):
            SecurityValidator.validate_positive_integer(-1, "block_height")


class TestTimestampValidation:
    """Test validate_timestamp function"""

    def test_validate_valid_timestamp(self):
        """Test validating valid current timestamp"""
        now = time.time()
        result = SecurityValidator.validate_timestamp(now)
        assert result == now

    def test_validate_timestamp_not_number(self):
        """Test rejecting non-number timestamp"""
        with pytest.raises(ValidationError, match="must be a number"):
            SecurityValidator.validate_timestamp("not_a_number")

    def test_validate_timestamp_too_old(self):
        """Test rejecting timestamp before year 2000"""
        with pytest.raises(ValidationError, match="too old"):
            SecurityValidator.validate_timestamp(946684799)  # Before 2000-01-01

    def test_validate_timestamp_too_far_future(self):
        """Test rejecting timestamp after year 2100"""
        with pytest.raises(ValidationError, match="too far in future"):
            SecurityValidator.validate_timestamp(4102444801)  # After 2100-01-01

    def test_validate_timestamp_clock_drift(self):
        """Test rejecting timestamp beyond allowed clock drift"""
        future = time.time() + 7201  # 2 hours + 1 second
        with pytest.raises(ValidationError, match="too far in future"):
            SecurityValidator.validate_timestamp(future)

    def test_validate_timestamp_within_clock_drift(self):
        """Test accepting timestamp within allowed clock drift"""
        future = time.time() + 3600  # 1 hour in future (allowed)
        result = SecurityValidator.validate_timestamp(future)
        assert result == future

    def test_validate_timestamp_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="created_at"):
            SecurityValidator.validate_timestamp(0, "created_at")


class TestHexStringValidation:
    """Test validate_hex_string function"""

    def test_validate_valid_hex(self):
        """Test validating valid hex string"""
        result = SecurityValidator.validate_hex_string("abcdef123456")
        assert result == "abcdef123456"

    def test_validate_hex_uppercase(self):
        """Test hex is converted to lowercase"""
        result = SecurityValidator.validate_hex_string("ABCDEF")
        assert result == "abcdef"

    def test_validate_hex_not_string(self):
        """Test rejecting non-string input"""
        with pytest.raises(ValidationError, match="must be a string"):
            SecurityValidator.validate_hex_string(12345)

    def test_validate_hex_invalid_characters(self):
        """Test rejecting non-hex characters"""
        with pytest.raises(ValidationError, match="hexadecimal characters"):
            SecurityValidator.validate_hex_string("xyz123")

    def test_validate_hex_exact_length(self):
        """Test validating hex with exact length requirement"""
        result = SecurityValidator.validate_hex_string("abcd", exact_length=4)
        assert result == "abcd"

    def test_validate_hex_wrong_length(self):
        """Test rejecting hex with wrong length"""
        with pytest.raises(ValidationError, match="must be exactly 64 characters"):
            SecurityValidator.validate_hex_string("abcd", exact_length=64)

    def test_validate_hex_custom_field_name(self):
        """Test custom field name in error message"""
        with pytest.raises(ValidationError, match="transaction_hash"):
            SecurityValidator.validate_hex_string("xyz", "transaction_hash")


class TestNetworkTypeValidation:
    """Test validate_network_type function"""

    def test_validate_testnet(self):
        """Test validating testnet"""
        result = SecurityValidator.validate_network_type("testnet")
        assert result == "testnet"

    def test_validate_mainnet(self):
        """Test validating mainnet"""
        result = SecurityValidator.validate_network_type("mainnet")
        assert result == "mainnet"

    def test_validate_network_uppercase(self):
        """Test network type is converted to lowercase"""
        result = SecurityValidator.validate_network_type("TESTNET")
        assert result == "testnet"

    def test_validate_network_not_string(self):
        """Test rejecting non-string network type"""
        with pytest.raises(ValidationError, match="must be a string"):
            SecurityValidator.validate_network_type(123)

    def test_validate_network_invalid(self):
        """Test rejecting invalid network type"""
        with pytest.raises(ValidationError, match="must be 'testnet' or 'mainnet'"):
            SecurityValidator.validate_network_type("devnet")


class TestSanitizeForLogging:
    """Test sanitize_for_logging function"""

    def test_sanitize_dict_with_sensitive_keys(self):
        """Test sanitizing dictionary removes sensitive keys"""
        data = {
            "address": "XAI" + "a" * 40,
            "amount": 10.5,
            "ip": "192.168.1.1",
            "email": "user@example.com"
        }

        result = SecurityValidator.sanitize_for_logging(data)

        assert "ip" not in result
        assert "email" not in result
        assert "amount" in result

    def test_sanitize_dict_truncates_address(self):
        """Test sanitizing dictionary truncates long addresses"""
        long_address = "XAI" + "a" * 40
        data = {"address": long_address}

        result = SecurityValidator.sanitize_for_logging(data)

        assert "..." in result

    def test_sanitize_long_string(self):
        """Test sanitizing long string truncates it"""
        long_string = "a" * 200
        result = SecurityValidator.sanitize_for_logging(long_string)

        assert "truncated" in result
        assert len(result) < len(long_string)

    def test_sanitize_short_string(self):
        """Test sanitizing short string keeps it as is"""
        short_string = "test"
        result = SecurityValidator.sanitize_for_logging(short_string)

        assert result == short_string

    def test_sanitize_other_types(self):
        """Test sanitizing other types converts to string"""
        result = SecurityValidator.sanitize_for_logging(12345)
        assert result == "12345"


class TestValidateTransactionData:
    """Test validate_transaction_data convenience function"""

    def test_validate_complete_transaction_data(self):
        """Test validating complete transaction data"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 10.5,
            "fee": 0.24
        }

        result = validate_transaction_data(data)

        assert result["sender"] == data["sender"]
        assert result["recipient"] == data["recipient"]
        assert result["amount"] == 10.5
        assert result["fee"] == 0.24

    def test_validate_transaction_missing_sender(self):
        """Test rejecting transaction data without sender"""
        data = {
            "recipient": "XAI" + "b" * 40,
            "amount": 10.5
        }

        with pytest.raises(ValidationError, match="Missing required field: sender"):
            validate_transaction_data(data)

    def test_validate_transaction_missing_recipient(self):
        """Test rejecting transaction data without recipient"""
        data = {
            "sender": "XAI" + "a" * 40,
            "amount": 10.5
        }

        with pytest.raises(ValidationError, match="Missing required field: recipient"):
            validate_transaction_data(data)

    def test_validate_transaction_missing_amount(self):
        """Test rejecting transaction data without amount"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40
        }

        with pytest.raises(ValidationError, match="Missing required field: amount"):
            validate_transaction_data(data)

    def test_validate_transaction_default_fee(self):
        """Test default fee is applied"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 10.5
        }

        result = validate_transaction_data(data)

        assert result["fee"] == 0.24

    def test_validate_transaction_with_private_key(self):
        """Test validating transaction data with private key"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 10.5,
            "private_key": "a" * 64
        }

        result = validate_transaction_data(data)

        assert result["private_key"] == "a" * 64


class TestValidateAPIRequest:
    """Test validate_api_request convenience function"""

    def test_validate_small_api_request(self):
        """Test validating small API request"""
        data = {"action": "transfer", "amount": 10.5}

        result = validate_api_request(data)

        assert result == data

    def test_validate_api_request_too_large(self):
        """Test rejecting API request that is too large"""
        large_data = {"data": "a" * (SecurityValidator.MAX_JSON_SIZE + 1)}

        with pytest.raises(ValidationError, match="Request too large"):
            validate_api_request(large_data)

    def test_validate_api_request_custom_max_size(self):
        """Test validating API request with custom max size"""
        data = {"data": "a" * 1000}

        with pytest.raises(ValidationError, match="Request too large"):
            validate_api_request(data, max_size=500)


class TestSecurityLogging:
    """Test log_security_event function"""

    def test_log_security_event_info(self):
        """Test logging INFO level security event"""
        try:
            log_security_event("test_event", {"detail": "test"}, "INFO")
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"log_security_event raised {e}")

    def test_log_security_event_warning(self):
        try:
            log_security_event("test_event", {"detail": "test"}, "WARNING")
        except Exception as e:
            pytest.fail(f"log_security_event raised {e}")

    def test_log_security_event_error(self):
        try:
            log_security_event("test_event", {"detail": "test"}, "ERROR")
        except Exception as e:
            pytest.fail(f"log_security_event raised {e}")

    def test_log_security_event_critical(self):
        try:
            log_security_event("test_event", {"detail": "test"}, "CRITICAL")
        except Exception as e:
            pytest.fail(f"log_security_event raised {e}")

    def test_log_security_event_default_severity(self):
        try:
            log_security_event("test_event", {"detail": "test"})
        except Exception as e:
            pytest.fail(f"log_security_event raised {e}")


class TestSecurityEventRouterDispatch:
    """Ensure SecurityEventRouter dispatches to sinks."""

    def setup_method(self):
        self._original_sinks = list(SecurityEventRouter._sinks)
        SecurityEventRouter._sinks = []

    def teardown_method(self):
        SecurityEventRouter._sinks = self._original_sinks

    def test_sink_invoked_on_dispatch(self):
        captured = []

        def sink(event_type, details, severity):
            captured.append((event_type, severity, details))

        SecurityEventRouter.register_sink(sink)
        log_security_event("router_event", {"detail": "value"}, "WARNING")

        assert captured == [("router_event", "WARNING", {"detail": "value"})]


class TestSecurityWebhookSink:
    """Test the webhook sink helper used for external alerts."""

    @patch("xai.core.node._SecurityWebhookForwarder")
    def test_webhook_sink_posts_payload(self, mock_forwarder):
        instance = mock_forwarder.return_value
        sink = BlockchainNode._create_security_webhook_sink(
            "https://example.com/hook", "token123", timeout=2
        )
        assert sink is not None

        sink("api_key_audit", {"key": "123"}, "WARNING")

        instance.enqueue.assert_called_once()
        payload = instance.enqueue.call_args[0][0]
        assert payload["event_type"] == "api_key_audit"
        assert payload["severity"] == "WARNING"

    @patch("xai.core.node._SecurityWebhookForwarder")
    def test_webhook_sink_ignores_info_events(self, mock_forwarder):
        sink = BlockchainNode._create_security_webhook_sink("https://example.com/hook")
        assert sink is not None

        sink("info_event", {}, "INFO")
        mock_forwarder.return_value.enqueue.assert_not_called()
        mock_forwarder.return_value.enqueue.assert_not_called()


class TestSecurityWebhookForwarder:
    """Validate retry/backoff on webhook forwarding."""

    def test_forwarder_retries_and_succeeds(self):
        with patch(
            "xai.core.node.requests.post",
            side_effect=[Exception("boom"), MagicMock()],
        ) as mock_post, patch("xai.core.node.time.sleep") as mock_sleep:
            forwarder = _SecurityWebhookForwarder(
                "https://example.com/hook",
                {"Authorization": "Bearer token"},
                timeout=1,
                max_retries=2,
                backoff=0.01,
                max_queue=10,
                queue_path=None,
            )
            payload = {"event_type": "audit", "severity": "WARNING"}
            forwarder.enqueue(payload)
            forwarder.queue.join()

            assert mock_post.call_count == 2
            mock_sleep.assert_called()

    def test_forwarder_drops_when_queue_full(self):
        forwarder = _SecurityWebhookForwarder(
            "https://example.com/hook",
            {},
            timeout=1,
            max_retries=1,
            max_queue=1,
            start_worker=False,
            queue_path=None,
        )
        forwarder.enqueue({"event_type": "one"})
        forwarder.enqueue({"event_type": "two"})
        assert forwarder.dropped_events == 1

    def test_forwarder_persists_queue(self, tmp_path):
        queue_file = tmp_path / "queue.json"
        forwarder = _SecurityWebhookForwarder(
            "https://example.com/hook",
            {},
            timeout=1,
            max_retries=1,
            max_queue=5,
            start_worker=False,
            queue_path=str(queue_file),
        )
        forwarder.enqueue({"event_type": "persist", "severity": "WARNING"})
        assert queue_file.exists()
        with queue_file.open("rb") as handle:
            contents = handle.read().decode("utf-8")
            data = json.loads(contents)
            assert data[0]["event_type"] == "persist"

        restored = _SecurityWebhookForwarder(
            "https://example.com/hook",
            {},
            timeout=1,
            max_retries=1,
            max_queue=5,
            start_worker=False,
            queue_path=str(queue_file),
        )
        assert restored.queue.qsize() == 1

    def test_forwarder_encrypted_queue(self, tmp_path):
        queue_file = tmp_path / "queue.enc"
        key = Fernet.generate_key().decode("utf-8")
        forwarder = _SecurityWebhookForwarder(
            "https://example.com/hook",
            {},
            timeout=1,
            max_retries=1,
            max_queue=5,
            start_worker=False,
            queue_path=str(queue_file),
            encryption_key=key,
        )
        payload = {"event_type": "secure", "severity": "CRITICAL"}
        forwarder.enqueue(payload)
        restored = _SecurityWebhookForwarder(
            "https://example.com/hook",
            {},
            timeout=1,
            max_retries=1,
            max_queue=5,
            start_worker=False,
            queue_path=str(queue_file),
            encryption_key=key,
        )
        assert restored.queue.qsize() == 1

class TestValidationErrorException:
    """Test ValidationError exception class"""

    def test_validation_error_creation(self):
        """Test creating ValidationError"""
        error = ValidationError("Test error")
        assert str(error) == "Test error"

    def test_validation_error_is_exception(self):
        """Test ValidationError is an Exception"""
        assert issubclass(ValidationError, Exception)

    def test_validation_error_can_be_raised(self):
        """Test ValidationError can be raised and caught"""
        with pytest.raises(ValidationError):
            raise ValidationError("Test error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
