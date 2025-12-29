"""
Comprehensive Security Validation Tests

Tests for 100% coverage of security_validation.py module.
Tests all input validation, sanitization, and security logging functions.
"""

import pytest
import json
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from xai.core.security.security_validation import (
    SecurityValidator,
    ValidationError,
    log_security_event,
    validate_transaction_data,
    validate_api_request,
)


@pytest.mark.security
class TestLogSecurityEvent:
    """Test security event logging functionality"""

    def test_log_info_event(self, caplog):
        """Test logging INFO level security event"""
        with caplog.at_level(logging.INFO, logger="xai.security"):
            log_security_event("test_event", {"key": "value"}, severity="INFO")

        assert len(caplog.records) > 0
        assert "test_event" in caplog.text

    def test_log_warning_event(self, caplog):
        """Test logging WARNING level security event"""
        with caplog.at_level(logging.WARNING, logger="xai.security"):
            log_security_event("warning_event", {"alert": "test"}, severity="WARNING")

        assert len(caplog.records) > 0
        record = caplog.records[0]
        assert record.levelname == "WARNING"

    def test_log_error_event(self, caplog):
        """Test logging ERROR level security event"""
        with caplog.at_level(logging.ERROR, logger="xai.security"):
            log_security_event("error_event", {"error": "test"}, severity="ERROR")

        assert len(caplog.records) > 0
        record = caplog.records[0]
        assert record.levelname == "ERROR"

    def test_log_critical_event(self, caplog):
        """Test logging CRITICAL level security event"""
        with caplog.at_level(logging.CRITICAL, logger="xai.security"):
            log_security_event("critical_event", {"critical": "test"}, severity="CRITICAL")

        assert len(caplog.records) > 0
        record = caplog.records[0]
        assert record.levelname == "CRITICAL"

    def test_log_event_structure(self, caplog):
        """Test that logged events have correct JSON structure"""
        with caplog.at_level(logging.INFO, logger="xai.security"):
            log_security_event("structured_event", {"data": "value"}, severity="INFO")

        assert len(caplog.records) > 0
        log_message = caplog.records[0].getMessage()

        # Should be valid JSON
        parsed = json.loads(log_message)
        assert "timestamp" in parsed
        assert "event_type" in parsed
        assert parsed["event_type"] == "structured_event"
        assert "severity" in parsed
        assert parsed["severity"] == "INFO"
        assert "details" in parsed


@pytest.mark.security
class TestValidateAmount:
    """Test amount validation"""

    def test_valid_positive_amount(self):
        """Test validation of valid positive amounts"""
        validator = SecurityValidator()

        assert validator.validate_amount(100.0) == 100.0
        assert validator.validate_amount(0.00000001) == 0.00000001
        assert validator.validate_amount(1000000.0) == 1000000.0

    def test_reject_zero_amount_in_validator(self):
        """Test that zero amounts are rejected (security requirement)"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be zero"):
            validator.validate_amount(0)

    def test_reject_negative_amount(self):
        """Test rejection of negative amounts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be negative"):
            validator.validate_amount(-1.0)

        with pytest.raises(ValidationError, match="cannot be negative"):
            validator.validate_amount(-0.01)

    def test_reject_non_numeric_amount(self):
        """Test rejection of non-numeric amounts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be numeric"):
            validator.validate_amount("100")

        with pytest.raises(ValidationError, match="must be numeric"):
            validator.validate_amount(None)

        with pytest.raises(ValidationError, match="must be numeric"):
            validator.validate_amount([])

    def test_reject_nan_amount(self):
        """Test rejection of NaN amounts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be NaN"):
            validator.validate_amount(float('nan'))

    def test_reject_infinity_amount(self):
        """Test rejection of infinite amounts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be infinite"):
            validator.validate_amount(float('inf'))

        with pytest.raises(ValidationError, match="cannot be infinite"):
            validator.validate_amount(float('-inf'))

    def test_reject_amount_below_minimum(self):
        """Test rejection of amounts below minimum"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="too small"):
            validator.validate_amount(0.000000001)  # Smaller than MIN_AMOUNT

    def test_reject_amount_above_maximum(self):
        """Test rejection of amounts above maximum"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="exceeds maximum"):
            validator.validate_amount(SecurityValidator.MAX_SUPPLY + 1)

    def test_precision_rounding(self):
        """Test automatic precision rounding to 8 decimal places"""
        validator = SecurityValidator()

        # Should round to 8 decimals
        result = validator.validate_amount(1.123456789)
        assert result == 1.12345679  # Rounded to 8 decimals

    def test_amount_field_name_in_error(self):
        """Test that field name appears in error messages"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="price"):
            validator.validate_amount(-1.0, "price")

    def test_integer_amount_conversion(self):
        """Test that integer amounts are converted to float"""
        validator = SecurityValidator()

        result = validator.validate_amount(100)
        assert isinstance(result, float)
        assert result == 100.0


@pytest.mark.security
class TestValidateAddress:
    """Test address validation"""

    def test_valid_xai_address(self):
        """Test validation of valid XAI addresses"""
        validator = SecurityValidator()

        valid_addr = "XAI" + "a" * 40
        assert validator.validate_address(valid_addr) == valid_addr

    def test_valid_xai_address(self):
        """Test validation of valid XAI addresses"""
        validator = SecurityValidator()

        valid_addr = "XAI" + "b" * 40
        assert validator.validate_address(valid_addr) == valid_addr

    def test_valid_txai_address(self):
        """Test validation of valid TXAI addresses"""
        validator = SecurityValidator()

        valid_addr = "TXAI" + "c" * 40
        assert validator.validate_address(valid_addr) == valid_addr

    def test_coinbase_address(self):
        """Test that COINBASE is accepted as special address"""
        validator = SecurityValidator()

        assert validator.validate_address("COINBASE") == "COINBASE"

    def test_reject_non_string_address(self):
        """Test rejection of non-string addresses"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_address(123)

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_address(None)

    def test_reject_empty_address(self):
        """Test rejection of empty addresses"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate_address("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate_address("   ")

    def test_reject_short_address(self):
        """Test rejection of addresses that are too short"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="too short"):
            validator.validate_address("XAI123")

    def test_reject_long_address(self):
        """Test rejection of addresses that are too long"""
        validator = SecurityValidator()

        long_addr = "XAI" + "a" * 200
        with pytest.raises(ValidationError, match="too long"):
            validator.validate_address(long_addr)

    def test_reject_invalid_prefix(self):
        """Test rejection of addresses with invalid prefix"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must start with"):
            validator.validate_address("INVALID" + "a" * 40)

    def test_reject_non_hex_characters(self):
        """Test rejection of addresses with non-hexadecimal characters"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="Invalid address format"):
            validator.validate_address("XAI" + "z" * 40)

    def test_sql_injection_detection(self, caplog):
        """Test detection of SQL injection attempts"""
        validator = SecurityValidator()

        with caplog.at_level(logging.WARNING, logger="xai.security"):
            with pytest.raises(ValidationError, match="invalid or dangerous characters"):
                validator.validate_address("XAI'; DROP TABLE users; --aaaaaaaaaaaaaa")

        # Should log security event
        assert any("injection_attempt_detected" in record.getMessage() for record in caplog.records)

    def test_xss_detection(self, caplog):
        """Test detection of XSS attempts"""
        validator = SecurityValidator()

        with caplog.at_level(logging.WARNING, logger="xai.security"):
            with pytest.raises(ValidationError, match="invalid or dangerous characters"):
                validator.validate_address("XAI<script>alert('xss')</script>aaaaaaaaaa")

    def test_command_injection_detection(self, caplog):
        """Test detection of command injection attempts"""
        validator = SecurityValidator()

        dangerous_chars = [
            "XAI; rm -rf /aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "XAI$(whoami)aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "XAI`ls`aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "XAI|cataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ]

        for addr in dangerous_chars:
            with pytest.raises(ValidationError):
                validator.validate_address(addr)

    def test_path_traversal_detection(self, caplog):
        """Test detection of path traversal attempts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            validator.validate_address("XAI../../../etc/passwdaaaaaaaaaaaaaaaaaaaa")

    def test_hex_escape_detection(self, caplog):
        """Test detection of hex escape sequences"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            validator.validate_address("XAI\\x41\\x41aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_url_encoding_detection(self, caplog):
        """Test detection of URL encoding attempts"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="invalid or dangerous characters"):
            validator.validate_address("XAI%20%20aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_address_whitespace_stripping(self):
        """Test that whitespace is stripped from addresses"""
        validator = SecurityValidator()

        addr_with_space = "  " + "XAI" + "a" * 40 + "  "
        result = validator.validate_address(addr_with_space)
        assert result == "XAI" + "a" * 40


@pytest.mark.security
class TestValidateFee:
    """Test fee validation"""

    def test_valid_fee(self):
        """Test validation of valid fees"""
        validator = SecurityValidator()

        assert validator.validate_fee(0.24) == 0.24
        assert validator.validate_fee(1.0) == 1.0

    def test_reject_excessive_fee(self):
        """Test rejection of fees above maximum"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="exceeds maximum"):
            validator.validate_fee(SecurityValidator.MAX_FEE + 1)

    def test_reject_negative_fee(self):
        """Test rejection of negative fees"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="cannot be negative"):
            validator.validate_fee(-0.1)

    def test_zero_fee(self):
        """Test that zero fee is valid"""
        validator = SecurityValidator()

        assert validator.validate_fee(0) == 0


@pytest.mark.security
class TestValidateString:
    """Test string validation"""

    def test_valid_string(self):
        """Test validation of valid strings"""
        validator = SecurityValidator()

        assert validator.validate_string("Hello World") == "Hello World"
        assert validator.validate_string("test123") == "test123"

    def test_reject_non_string(self):
        """Test rejection of non-string values"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_string(123)

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_string(None)

    def test_reject_oversized_string(self):
        """Test rejection of strings exceeding max length"""
        validator = SecurityValidator()

        long_string = "a" * (SecurityValidator.MAX_STRING_LENGTH + 1)
        with pytest.raises(ValidationError, match="too long"):
            validator.validate_string(long_string)

    def test_custom_max_length(self):
        """Test validation with custom max length"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="too long"):
            validator.validate_string("a" * 101, max_length=100)

    def test_reject_control_characters(self):
        """Test rejection of control characters"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="contains invalid control characters"):
            validator.validate_string("test\x00data")

        with pytest.raises(ValidationError, match="contains invalid control characters"):
            validator.validate_string("test\x01data")

    def test_allow_newline_characters(self):
        """Test that newline, carriage return, and tab are allowed"""
        validator = SecurityValidator()

        assert validator.validate_string("line1\nline2") == "line1\nline2"
        assert validator.validate_string("col1\tcol2") == "col1\tcol2"
        assert validator.validate_string("line\rreturn") == "line\rreturn"

    def test_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped"""
        validator = SecurityValidator()

        assert validator.validate_string("  test  ") == "test"


@pytest.mark.security
class TestValidatePositiveInteger:
    """Test positive integer validation"""

    def test_valid_positive_integer(self):
        """Test validation of valid positive integers"""
        validator = SecurityValidator()

        assert validator.validate_positive_integer(1) == 1
        assert validator.validate_positive_integer(100) == 100
        assert validator.validate_positive_integer(999999) == 999999

    def test_zero_integer(self):
        """Test that zero is valid"""
        validator = SecurityValidator()

        assert validator.validate_positive_integer(0) == 0

    def test_reject_negative_integer(self):
        """Test rejection of negative integers"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be >="):
            validator.validate_positive_integer(-1)

    def test_reject_non_integer(self):
        """Test rejection of non-integer values that cannot be converted"""
        validator = SecurityValidator()

        # Pass a value that cannot be converted to integer
        with pytest.raises(ValidationError, match="must be an integer"):
            validator.validate_positive_integer([1, 2, 3])

    def test_string_to_integer_conversion(self):
        """Test conversion of numeric strings to integers"""
        validator = SecurityValidator()

        assert validator.validate_positive_integer("100") == 100

    def test_reject_too_large_integer(self):
        """Test rejection of integers exceeding max safe value"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be <="):
            validator.validate_positive_integer(2**63)


@pytest.mark.security
class TestValidateTimestamp:
    """Test timestamp validation"""

    def test_valid_current_timestamp(self):
        """Test validation of current timestamp"""
        validator = SecurityValidator()

        current_time = datetime.now(timezone.utc).timestamp()
        assert validator.validate_timestamp(current_time) == current_time

    def test_valid_past_timestamp(self):
        """Test validation of recent past timestamp"""
        validator = SecurityValidator()

        # Timestamp from 2020
        past_time = 1577836800.0  # 2020-01-01
        assert validator.validate_timestamp(past_time) == past_time

    def test_reject_non_numeric_timestamp(self):
        """Test rejection of non-numeric timestamps"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be a number"):
            validator.validate_timestamp("not a number")

    def test_reject_too_old_timestamp(self):
        """Test rejection of timestamps before year 2000"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="too old"):
            validator.validate_timestamp(946684799)  # Before 2000-01-01

    def test_reject_too_far_future_timestamp(self):
        """Test rejection of timestamps beyond 2100"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="too far in future"):
            validator.validate_timestamp(4102444801)  # After 2100-01-01

    def test_reject_timestamp_with_clock_drift(self):
        """Test rejection of timestamps more than 2 hours in future"""
        validator = SecurityValidator()

        current_time = datetime.now(timezone.utc).timestamp()
        future_time = current_time + 7201  # More than 2 hours

        with pytest.raises(ValidationError, match="too far in future"):
            validator.validate_timestamp(future_time)

    def test_allow_small_clock_drift(self):
        """Test that small clock drift (< 2 hours) is allowed"""
        validator = SecurityValidator()

        current_time = datetime.now(timezone.utc).timestamp()
        slightly_future = current_time + 3600  # 1 hour

        assert validator.validate_timestamp(slightly_future) == slightly_future


@pytest.mark.security
class TestValidateHexString:
    """Test hexadecimal string validation"""

    def test_valid_hex_string(self):
        """Test validation of valid hex strings"""
        validator = SecurityValidator()

        assert validator.validate_hex_string("abcdef123456") == "abcdef123456"
        assert validator.validate_hex_string("ABCDEF123456") == "abcdef123456"  # Lowercased

    def test_reject_non_string(self):
        """Test rejection of non-string values"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_hex_string(123)

    def test_reject_non_hex_characters(self):
        """Test rejection of non-hexadecimal characters"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must contain only hexadecimal characters"):
            validator.validate_hex_string("xyz123")

    def test_exact_length_validation(self):
        """Test exact length validation"""
        validator = SecurityValidator()

        # Should pass
        assert validator.validate_hex_string("ab" * 32, exact_length=64) == "ab" * 32

        # Should fail
        with pytest.raises(ValidationError, match="exactly 64 characters"):
            validator.validate_hex_string("ab" * 31, exact_length=64)

    def test_hex_string_lowercase_conversion(self):
        """Test that hex strings are converted to lowercase"""
        validator = SecurityValidator()

        result = validator.validate_hex_string("ABCDEF")
        assert result == "abcdef"


@pytest.mark.security
class TestValidateNetworkType:
    """Test network type validation"""

    def test_valid_testnet(self):
        """Test validation of testnet"""
        validator = SecurityValidator()

        assert validator.validate_network_type("testnet") == "testnet"
        assert validator.validate_network_type("TESTNET") == "testnet"
        assert validator.validate_network_type("  testnet  ") == "testnet"

    def test_valid_mainnet(self):
        """Test validation of mainnet"""
        validator = SecurityValidator()

        assert validator.validate_network_type("mainnet") == "mainnet"
        assert validator.validate_network_type("MAINNET") == "mainnet"

    def test_reject_invalid_network(self):
        """Test rejection of invalid network types"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be 'testnet' or 'mainnet'"):
            validator.validate_network_type("devnet")

        with pytest.raises(ValidationError, match="must be 'testnet' or 'mainnet'"):
            validator.validate_network_type("invalid")

    def test_reject_non_string_network(self):
        """Test rejection of non-string network types"""
        validator = SecurityValidator()

        with pytest.raises(ValidationError, match="must be a string"):
            validator.validate_network_type(123)


@pytest.mark.security
class TestSanitizeForLogging:
    """Test data sanitization for logging"""

    def test_sanitize_dict_with_sensitive_keys(self):
        """Test removal of sensitive keys from dictionaries"""
        validator = SecurityValidator()

        data = {
            "ip": "192.168.1.1",
            "ip_address": "10.0.0.1",
            "user": "admin",
            "email": "test@example.com",
            "phone": "555-1234",
            "location": "New York",
            "geo": "US",
            "safe_key": "safe_value"
        }

        result = validator.sanitize_for_logging(data)

        # Sensitive keys should be removed
        assert "ip" not in result
        assert "email" not in result
        assert "safe_key" in result or "safe_value" in result

    def test_sanitize_dict_with_address_truncation(self):
        """Test truncation of long addresses in dictionaries"""
        validator = SecurityValidator()

        long_address = "XAI" + "a" * 50
        data = {"address": long_address}

        result = validator.sanitize_for_logging(data)

        # Address should be truncated
        assert "..." in result

    def test_sanitize_long_string(self):
        """Test truncation of long strings"""
        validator = SecurityValidator()

        long_string = "a" * 200
        result = validator.sanitize_for_logging(long_string)

        assert "truncated" in result
        assert len(result) < len(long_string)

    def test_sanitize_short_string(self):
        """Test that short strings are not truncated"""
        validator = SecurityValidator()

        short_string = "test"
        result = validator.sanitize_for_logging(short_string)

        assert result == short_string

    def test_sanitize_other_types(self):
        """Test sanitization of other data types"""
        validator = SecurityValidator()

        assert validator.sanitize_for_logging(123) == "123"
        assert validator.sanitize_for_logging(None) == "None"
        assert validator.sanitize_for_logging([1, 2, 3]) == "[1, 2, 3]"


@pytest.mark.security
class TestValidateTransactionData:
    """Test complete transaction data validation"""

    def test_valid_transaction_data(self):
        """Test validation of complete valid transaction data"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 100.0,
            "fee": 0.24
        }

        result = validate_transaction_data(data)

        assert result["sender"] == data["sender"]
        assert result["recipient"] == data["recipient"]
        assert result["amount"] == data["amount"]
        assert result["fee"] == data["fee"]

    def test_transaction_with_private_key(self):
        """Test validation of transaction with private key"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 100.0,
            "fee": 0.24,
            "private_key": "a" * 64
        }

        result = validate_transaction_data(data)

        assert "private_key" in result
        assert result["private_key"] == "a" * 64

    def test_missing_sender_field(self):
        """Test rejection when sender field is missing"""
        data = {
            "recipient": "XAI" + "b" * 40,
            "amount": 100.0
        }

        with pytest.raises(ValidationError, match="Missing required field: sender"):
            validate_transaction_data(data)

    def test_missing_recipient_field(self):
        """Test rejection when recipient field is missing"""
        data = {
            "sender": "XAI" + "a" * 40,
            "amount": 100.0
        }

        with pytest.raises(ValidationError, match="Missing required field: recipient"):
            validate_transaction_data(data)

    def test_missing_amount_field(self):
        """Test rejection when amount field is missing"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40
        }

        with pytest.raises(ValidationError, match="Missing required field: amount"):
            validate_transaction_data(data)

    def test_default_fee_value(self):
        """Test that default fee is applied when not provided"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 100.0
        }

        result = validate_transaction_data(data)

        assert result["fee"] == 0.24

    def test_invalid_private_key_length(self):
        """Test rejection of invalid private key length"""
        data = {
            "sender": "XAI" + "a" * 40,
            "recipient": "XAI" + "b" * 40,
            "amount": 100.0,
            "fee": 0.24,
            "private_key": "a" * 32  # Wrong length
        }

        with pytest.raises(ValidationError, match="exactly 64 characters"):
            validate_transaction_data(data)


@pytest.mark.security
class TestValidateApiRequest:
    """Test API request validation"""

    def test_valid_api_request(self):
        """Test validation of valid API request"""
        data = {"key": "value", "number": 123}

        result = validate_api_request(data)

        assert result == data

    def test_reject_oversized_request(self):
        """Test rejection of oversized API requests"""
        # Create large request
        large_data = {"data": "x" * 2000000}

        with pytest.raises(ValidationError, match="too large"):
            validate_api_request(large_data)

    def test_custom_max_size(self):
        """Test validation with custom max size"""
        data = {"key": "value"}

        # Should pass with large limit
        result = validate_api_request(data, max_size=1000000)
        assert result == data

        # Should fail with small limit
        with pytest.raises(ValidationError, match="too large"):
            validate_api_request(data, max_size=10)


@pytest.mark.security
class TestValidationErrorException:
    """Test ValidationError exception class"""

    def test_validation_error_creation(self):
        """Test creating ValidationError exception"""
        error = ValidationError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_validation_error_raise(self):
        """Test raising ValidationError exception"""
        with pytest.raises(ValidationError):
            raise ValidationError("Test error")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
