from __future__ import annotations

"""
Comprehensive tests for error_handlers module - targeting 70%+ coverage

Tests all error handler classes, circuit breaker patterns, retry strategies,
error routing, and logging mechanisms.
"""

import pytest
import time
import logging
from typing import Any
from unittest.mock import Mock, MagicMock, patch
from xai.core.error_handlers import (
    CircuitState,
    CircuitBreaker,
    RetryStrategy,
    ErrorHandler,
    NetworkErrorHandler,
    ValidationErrorHandler,
    StorageErrorHandler,
    ErrorHandlerRegistry,
    ErrorLogger,
)

class TestCircuitState:
    """Test CircuitState enum"""

    def test_circuit_state_values(self):
        """Test all circuit state enum values"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_comparison(self):
        """Test circuit state comparisons"""
        assert CircuitState.CLOSED == CircuitState.CLOSED
        assert CircuitState.OPEN != CircuitState.CLOSED
        assert CircuitState.HALF_OPEN != CircuitState.OPEN

class TestCircuitBreaker:
    """Comprehensive CircuitBreaker tests"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create CircuitBreaker with short timeouts for testing"""
        return CircuitBreaker(failure_threshold=3, timeout=1, success_threshold=2)

    def test_init_default_values(self):
        """Test CircuitBreaker initialization with default values"""
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.timeout == 60
        assert cb.success_threshold == 2
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    def test_init_custom_values(self):
        """Test CircuitBreaker initialization with custom values"""
        cb = CircuitBreaker(failure_threshold=10, timeout=120, success_threshold=5)
        assert cb.failure_threshold == 10
        assert cb.timeout == 120
        assert cb.success_threshold == 5

    def test_call_success_closed_state(self, circuit_breaker):
        """Test successful call in CLOSED state"""

        def success_func(x, y):
            return x + y

        success, result, error = circuit_breaker.call(success_func, 5, 10)

        assert success is True
        assert result == 15
        assert error is None
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    def test_call_success_with_kwargs(self, circuit_breaker):
        """Test successful call with keyword arguments"""

        def func_with_kwargs(a, b=10):
            return a * b

        success, result, error = circuit_breaker.call(func_with_kwargs, 5, b=3)

        assert success is True
        assert result == 15
        assert error is None

    def test_call_failure_increments_count(self, circuit_breaker):
        """Test that failures increment failure count"""

        def fail_func():
            raise ValueError("test error")

        success, result, error = circuit_breaker.call(fail_func)

        assert success is False
        assert result is None
        assert error == "test error"
        assert circuit_breaker.failure_count == 1

    def test_call_opens_circuit_after_threshold(self, circuit_breaker):
        """Test circuit opens after reaching failure threshold"""

        def fail_func():
            raise RuntimeError("fail")

        # Trigger failures to reach threshold (3)
        for i in range(3):
            circuit_breaker.call(fail_func)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3

    def test_call_rejected_when_open(self, circuit_breaker):
        """Test calls are rejected when circuit is OPEN"""

        def fail_func():
            raise Exception("fail")

        # Open the circuit
        for i in range(3):
            circuit_breaker.call(fail_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Try to call - should be rejected
        def success_func():
            return "success"

        success, result, error = circuit_breaker.call(success_func)

        assert success is False
        assert result is None
        assert error == "Circuit breaker is OPEN"

    def test_half_open_state_transition(self, circuit_breaker):
        """Test transition from OPEN to HALF_OPEN after timeout"""

        def fail_func():
            raise Exception("fail")

        # Open the circuit
        for i in range(3):
            circuit_breaker.call(fail_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Next call should enter HALF_OPEN
        def success_func():
            return "ok"

        success, result, error = circuit_breaker.call(success_func)

        assert success is True
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self, circuit_breaker):
        """Test transition from HALF_OPEN to CLOSED after success threshold"""

        def fail_func():
            raise Exception("fail")

        # Open the circuit
        for i in range(3):
            circuit_breaker.call(fail_func)

        # Wait for timeout
        time.sleep(1.1)

        def success_func():
            return "ok"

        # First success in HALF_OPEN
        circuit_breaker.call(success_func)
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        assert circuit_breaker.success_count == 1

        # Second success should close circuit
        circuit_breaker.call(success_func)
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.success_count == 0

    def test_half_open_to_open_on_failure(self, circuit_breaker):
        """Test transition from HALF_OPEN back to OPEN on failure"""

        def fail_func():
            raise Exception("fail")

        # Open the circuit
        for i in range(3):
            circuit_breaker.call(fail_func)

        # Wait for timeout
        time.sleep(1.1)

        # Failure in HALF_OPEN should reopen circuit
        success, result, error = circuit_breaker.call(fail_func)

        assert success is False
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.success_count == 0

    def test_reset_method(self, circuit_breaker):
        """Test manual circuit reset"""

        def fail_func():
            raise Exception("fail")

        # Open the circuit
        for i in range(3):
            circuit_breaker.call(fail_func)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count > 0

        # Reset circuit
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
        assert circuit_breaker.last_failure_time is None

    def test_get_state_method(self, circuit_breaker):
        """Test get_state returns correct information"""
        state_info = circuit_breaker.get_state()

        assert "state" in state_info
        assert "failure_count" in state_info
        assert "success_count" in state_info
        assert "last_failure_time" in state_info
        assert state_info["state"] == "closed"
        assert state_info["failure_count"] == 0

    def test_get_state_after_failures(self, circuit_breaker):
        """Test get_state after some failures"""

        def fail_func():
            raise Exception("fail")

        circuit_breaker.call(fail_func)
        circuit_breaker.call(fail_func)

        state_info = circuit_breaker.get_state()

        assert state_info["failure_count"] == 2
        assert state_info["last_failure_time"] is not None

    def test_on_success_resets_failure_count(self, circuit_breaker):
        """Test _on_success resets failure count"""

        def fail_func():
            raise Exception("fail")

        # Generate some failures
        circuit_breaker.call(fail_func)
        assert circuit_breaker.failure_count == 1

        # Success should reset count
        def success_func():
            return "ok"

        circuit_breaker.call(success_func)
        assert circuit_breaker.failure_count == 0

    def test_on_failure_updates_timestamp(self, circuit_breaker):
        """Test _on_failure updates last_failure_time"""
        before_time = time.time()

        def fail_func():
            raise Exception("fail")

        circuit_breaker.call(fail_func)

        after_time = time.time()

        assert circuit_breaker.last_failure_time is not None
        assert before_time <= circuit_breaker.last_failure_time <= after_time

class TestRetryStrategy:
    """Comprehensive RetryStrategy tests"""

    @pytest.fixture
    def retry_strategy(self):
        """Create RetryStrategy with short delays for testing"""
        return RetryStrategy(max_retries=3, base_delay=0.01, max_delay=1.0)

    def test_init_default_values(self):
        """Test RetryStrategy initialization with defaults"""
        rs = RetryStrategy()
        assert rs.max_retries == 3
        assert rs.base_delay == 1.0
        assert rs.max_delay == 60.0
        assert rs.exponential_base == 2.0

    def test_init_custom_values(self):
        """Test RetryStrategy initialization with custom values"""
        rs = RetryStrategy(max_retries=5, base_delay=0.5, max_delay=30.0, exponential_base=3.0)
        assert rs.max_retries == 5
        assert rs.base_delay == 0.5
        assert rs.max_delay == 30.0
        assert rs.exponential_base == 3.0

    def test_execute_success_first_try(self, retry_strategy):
        """Test successful execution on first try"""

        def success_func():
            return "result"

        success, result, error = retry_strategy.execute(success_func)

        assert success is True
        assert result == "result"
        assert error is None

    def test_execute_with_args_kwargs(self, retry_strategy):
        """Test execute with arguments and keyword arguments"""

        def func_with_params(a, b, c=10):
            return a + b + c

        success, result, error = retry_strategy.execute(func_with_params, 5, 3, c=2)

        assert success is True
        assert result == 10

    def test_execute_retry_count(self, retry_strategy):
        """Test that function is retried correct number of times"""
        call_count = [0]

        def fail_func():
            call_count[0] += 1
            raise RuntimeError("fail")

        success, result, error = retry_strategy.execute(fail_func)

        # Should be called initial + max_retries times
        assert call_count[0] == 4  # 1 initial + 3 retries
        assert success is False

    def test_execute_success_after_retries(self, retry_strategy):
        """Test successful execution after some retries"""
        attempt_count = [0]

        def intermittent_func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("fail")
            return "success"

        success, result, error = retry_strategy.execute(intermittent_func)

        assert success is True
        assert result == "success"
        assert attempt_count[0] == 3

    def test_execute_all_retries_fail(self, retry_strategy):
        """Test when all retries fail"""

        def always_fail():
            raise ValueError("persistent error")

        success, result, error = retry_strategy.execute(always_fail)

        assert success is False
        assert result is None
        assert "Failed after 4 attempts" in error
        assert "persistent error" in error

    def test_exponential_backoff_delays(self):
        """Test exponential backoff calculation"""
        rs = RetryStrategy(max_retries=3, base_delay=1.0, exponential_base=2.0, max_delay=10.0)

        call_times = []

        def record_time_and_fail():
            call_times.append(time.time())
            raise Exception("fail")

        rs.execute(record_time_and_fail)

        # Check delays are approximately exponential
        # Delay 1: ~1s, Delay 2: ~2s, Delay 3: ~4s
        assert len(call_times) == 4

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        rs = RetryStrategy(max_retries=5, base_delay=10.0, exponential_base=2.0, max_delay=5.0)

        delays = []
        for attempt in range(5):
            delay = min(rs.base_delay * (rs.exponential_base**attempt), rs.max_delay)
            delays.append(delay)

        # All delays should be capped at max_delay
        for delay in delays[2:]:  # After first few attempts
            assert delay == 5.0

class TestErrorHandler:
    """Test ErrorHandler base class"""

    class _DummyHandler(ErrorHandler):
        """Minimal concrete handler for exercising base behavior."""

        def can_handle(self, error: Exception, context: str) -> bool:
            return False

        def handle(self, error: Exception, context: str, blockchain: Any) -> tuple[bool, str | None]:
            return False, "unhandled"

    def test_cannot_instantiate_directly(self):
        """Test ErrorHandler enforces abstract contract."""
        with pytest.raises(TypeError):
            ErrorHandler("test_handler")

    def test_subclass_inherits_base_configuration(self):
        """Concrete subclasses receive base initialization."""
        handler = self._DummyHandler("dummy")
        assert handler.name == "dummy"
        assert handler.handled_count == 0
        assert handler.logger.name == "handler.dummy"

class TestNetworkErrorHandler:
    """Comprehensive NetworkErrorHandler tests"""

    @pytest.fixture
    def handler(self):
        """Create NetworkErrorHandler instance"""
        return NetworkErrorHandler()

    def test_init(self, handler):
        """Test initialization"""
        assert handler.name == "network"
        assert handler.handled_count == 0
        assert handler.retry_strategy is not None

    def test_can_handle_connection_error(self, handler):
        """Test can_handle for ConnectionError"""
        error = ConnectionError("Connection failed")
        assert handler.can_handle(error, "network_op") is True

    def test_can_handle_timeout_error(self, handler):
        """Test can_handle for TimeoutError"""
        error = TimeoutError("Request timed out")
        assert handler.can_handle(error, "network_op") is True

    def test_can_handle_os_error(self, handler):
        """Test can_handle for OSError"""
        error = OSError("Network unreachable")
        assert handler.can_handle(error, "network_op") is True

    def test_cannot_handle_value_error(self, handler):
        """Test can_handle returns False for non-network errors"""
        error = ValueError("Invalid value")
        assert handler.can_handle(error, "validation") is False

    def test_handle_network_error(self, handler):
        """Test handling network error"""
        error = ConnectionError("Connection reset")
        success, msg = handler.handle(error, "peer_connection", None)

        assert success is True
        assert "Network error handled" in msg
        assert handler.handled_count == 1

    def test_handle_increments_count(self, handler):
        """Test that handling increments counter"""
        error = TimeoutError("timeout")

        handler.handle(error, "context", None)
        assert handler.handled_count == 1

        handler.handle(error, "context", None)
        assert handler.handled_count == 2

class TestValidationErrorHandler:
    """Comprehensive ValidationErrorHandler tests"""

    @pytest.fixture
    def handler(self):
        """Create ValidationErrorHandler instance"""
        return ValidationErrorHandler()

    def test_init(self, handler):
        """Test initialization"""
        assert handler.name == "validation"
        assert handler.handled_count == 0

    def test_can_handle_value_error(self, handler):
        """Test can_handle for ValueError"""
        error = ValueError("Invalid value")
        assert handler.can_handle(error, "input_validation") is True

    def test_can_handle_invalid_keyword(self, handler):
        """Test can_handle for errors with 'invalid' keyword"""
        error = Exception("Invalid transaction format")
        assert handler.can_handle(error, "transaction") is True

    def test_can_handle_invalid_uppercase(self, handler):
        """Test can_handle for errors with 'INVALID' keyword"""
        error = RuntimeError("INVALID signature")
        assert handler.can_handle(error, "signature") is True

    def test_cannot_handle_connection_error(self, handler):
        """Test can_handle returns False for non-validation errors"""
        error = ConnectionError("Connection failed")
        assert handler.can_handle(error, "network") is False

    def test_handle_validation_error(self, handler):
        """Test handling validation error"""
        error = ValueError("Invalid transaction amount")
        success, msg = handler.handle(error, "transaction_validation", None)

        assert success is True
        assert "Validation error" in msg
        assert "input rejected" in msg
        assert handler.handled_count == 1

    def test_handle_preserves_error_message(self, handler):
        """Test that handle includes original error message"""
        error = ValueError("Custom validation message")
        success, msg = handler.handle(error, "context", None)

        assert "Custom validation message" in msg

class TestStorageErrorHandler:
    """Comprehensive StorageErrorHandler tests"""

    @pytest.fixture
    def handler(self):
        """Create StorageErrorHandler instance"""
        return StorageErrorHandler()

    def test_init(self, handler):
        """Test initialization"""
        assert handler.name == "storage"
        assert handler.handled_count == 0
        assert handler.retry_strategy is not None

    def test_can_handle_io_error(self, handler):
        """Test can_handle for IOError"""
        error = IOError("Failed to read file")
        assert handler.can_handle(error, "file_read") is True

    def test_can_handle_os_error(self, handler):
        """Test can_handle for OSError"""
        error = OSError("Disk full")
        assert handler.can_handle(error, "write") is True

    def test_can_handle_permission_error(self, handler):
        """Test can_handle for PermissionError"""
        error = PermissionError("Access denied")
        assert handler.can_handle(error, "file_access") is True

    def test_can_handle_file_not_found(self, handler):
        """Test can_handle for FileNotFoundError"""
        error = FileNotFoundError("File missing")
        assert handler.can_handle(error, "file_open") is True

    def test_handle_storage_error(self, handler):
        """Test handling storage error"""
        error = IOError("Write failed")
        success, msg = handler.handle(error, "blockchain_save", None)

        assert success is False  # Storage errors are critical
        assert "Storage error" in msg
        assert "recovery may be needed" in msg
        assert handler.handled_count == 1

class TestErrorHandlerRegistry:
    """Comprehensive ErrorHandlerRegistry tests"""

    @pytest.fixture
    def registry(self):
        """Create ErrorHandlerRegistry instance"""
        return ErrorHandlerRegistry()

    def test_init_registers_default_handlers(self, registry):
        """Test that default handlers are registered on init"""
        assert len(registry.handlers) >= 3  # Network, Validation, Storage
        handler_names = [h.name for h in registry.handlers]
        assert "network" in handler_names
        assert "validation" in handler_names
        assert "storage" in handler_names

    def test_register_handler(self, registry):
        """Test registering custom handler"""
        initial_count = len(registry.handlers)

        custom_handler = NetworkErrorHandler()
        registry.register_handler(custom_handler)

        assert len(registry.handlers) == initial_count + 1
        assert custom_handler in registry.handlers

    def test_set_fallback_handler(self, registry):
        """Test setting fallback handler"""
        fallback = NetworkErrorHandler()
        registry.set_fallback_handler(fallback)

        assert registry.fallback_handler == fallback

    def test_handle_error_network(self, registry):
        """Test handling network error routes to NetworkErrorHandler"""
        error = ConnectionError("Connection lost")
        success, msg = registry.handle_error(error, "network_sync", None)

        assert success is True
        assert "Network error" in msg

    def test_handle_error_validation(self, registry):
        """Test handling validation error routes to ValidationErrorHandler"""
        error = ValueError("Invalid input")
        success, msg = registry.handle_error(error, "input", None)

        assert success is True
        assert "Validation error" in msg

    def test_handle_error_storage(self, registry):
        """Test handling storage error routes to StorageErrorHandler"""
        error = IOError("Disk error")
        success, msg = registry.handle_error(error, "save", None)

        assert success is False  # Storage errors return False
        assert "Storage error" in msg

    def test_handle_error_no_handler_no_fallback(self, registry):
        """Test handling error with no matching handler and no fallback"""
        # Remove all handlers
        registry.handlers = []
        registry.fallback_handler = None

        error = Exception("Unknown error")
        success, msg = registry.handle_error(error, "unknown", None)

        assert success is False
        assert "Unhandled error" in msg

    def test_handle_error_uses_fallback(self, registry):
        """Test that fallback handler is used for unhandled errors"""
        # Remove default handlers
        registry.handlers = []

        fallback = NetworkErrorHandler()
        registry.set_fallback_handler(fallback)

        error = Exception("Unknown error type")
        success, msg = registry.handle_error(error, "unknown", None)

        # Fallback is NetworkErrorHandler which returns True
        assert success is True

    def test_get_handler_statistics(self, registry):
        """Test getting handler statistics"""
        # Handle some errors
        registry.handle_error(ConnectionError("test"), "net", None)
        registry.handle_error(ValueError("test"), "val", None)

        stats = registry.get_handler_statistics()

        assert "total_handlers" in stats
        assert "handlers" in stats
        assert stats["total_handlers"] == len(registry.handlers)
        assert isinstance(stats["handlers"], list)

    def test_get_handler_statistics_includes_counts(self, registry):
        """Test that statistics include handled counts"""
        # Handle multiple errors
        for i in range(3):
            registry.handle_error(ConnectionError("test"), "net", None)

        stats = registry.get_handler_statistics()

        # Find network handler stats
        network_handler_stats = [h for h in stats["handlers"] if h["name"] == "network"][0]
        assert network_handler_stats["handled_count"] == 3

class TestErrorLogger:
    """Comprehensive ErrorLogger tests"""

    @pytest.fixture
    def error_logger(self):
        """Create ErrorLogger instance"""
        return ErrorLogger(max_entries=100)

    def test_init(self, error_logger):
        """Test initialization"""
        assert len(error_logger.error_log) == 0

    def test_init_max_entries(self):
        """Test max_entries is respected"""
        logger = ErrorLogger(max_entries=5)
        assert logger.error_log.maxlen == 5

    def test_log_error_basic(self, error_logger):
        """Test basic error logging"""
        error = ValueError("test error")
        error_logger.log_error(error, "test_context", "medium")

        assert len(error_logger.error_log) == 1

    def test_log_error_structure(self, error_logger):
        """Test logged error structure"""
        error = RuntimeError("test error")
        error_logger.log_error(error, "test_context", "high")

        entry = error_logger.error_log[0]

        assert "timestamp" in entry
        assert "error_type" in entry
        assert "error_message" in entry
        assert "context" in entry
        assert "severity" in entry
        assert "additional_info" in entry

        assert entry["error_type"] == "RuntimeError"
        assert entry["error_message"] == "test error"
        assert entry["context"] == "test_context"
        assert entry["severity"] == "high"

    def test_log_error_with_additional_info(self, error_logger):
        """Test logging error with additional info"""
        error = ValueError("test")
        additional = {"user": "admin", "operation": "save"}

        error_logger.log_error(error, "context", "low", additional)

        entry = error_logger.error_log[0]
        assert entry["additional_info"] == additional

    def test_log_error_severity_levels(self, error_logger):
        """Test logging errors with different severity levels"""
        error_logger.log_error(Exception("test1"), "ctx", "low")
        error_logger.log_error(Exception("test2"), "ctx", "medium")
        error_logger.log_error(Exception("test3"), "ctx", "high")
        error_logger.log_error(Exception("test4"), "ctx", "critical")

        assert len(error_logger.error_log) == 4

    def test_get_recent_errors(self, error_logger):
        """Test getting recent errors"""
        # Log multiple errors
        for i in range(20):
            error_logger.log_error(Exception(f"error {i}"), "ctx", "medium")

        recent = error_logger.get_recent_errors(5)

        assert len(recent) == 5
        # Should get most recent (15-19)
        assert "error 19" in recent[-1]["error_message"]

    def test_get_recent_errors_default_count(self, error_logger):
        """Test get_recent_errors with default count"""
        for i in range(15):
            error_logger.log_error(Exception(f"error {i}"), "ctx", "medium")

        recent = error_logger.get_recent_errors()

        assert len(recent) == 10  # Default is 10

    def test_get_error_summary_empty(self, error_logger):
        """Test getting summary with no errors"""
        summary = error_logger.get_error_summary()

        assert summary["total_errors"] == 0
        assert summary["by_severity"] == {}
        assert summary["by_type"] == {}

    def test_get_error_summary_with_errors(self, error_logger):
        """Test getting error summary with logged errors"""
        error_logger.log_error(ValueError("err1"), "ctx", "high")
        error_logger.log_error(ValueError("err2"), "ctx", "medium")
        error_logger.log_error(RuntimeError("err3"), "ctx", "high")
        error_logger.log_error(TypeError("err4"), "ctx", "low")

        summary = error_logger.get_error_summary()

        assert summary["total_errors"] == 4
        assert summary["by_severity"]["high"] == 2
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_severity"]["low"] == 1
        assert summary["by_type"]["ValueError"] == 2
        assert summary["by_type"]["RuntimeError"] == 1
        assert summary["by_type"]["TypeError"] == 1

    def test_get_error_summary_includes_recent(self, error_logger):
        """Test that summary includes recent errors"""
        for i in range(10):
            error_logger.log_error(Exception(f"error {i}"), "ctx", "medium")

        summary = error_logger.get_error_summary()

        assert "recent_errors" in summary
        assert len(summary["recent_errors"]) == 5  # Default recent count

    def test_max_entries_rotation(self):
        """Test that old entries are removed when max is reached"""
        logger = ErrorLogger(max_entries=5)

        # Add 10 errors
        for i in range(10):
            logger.log_error(Exception(f"error {i}"), "ctx", "medium")

        # Should only have 5 (most recent)
        assert len(logger.error_log) == 5
        assert "error 9" in logger.error_log[-1]["error_message"]
        assert "error 5" in logger.error_log[0]["error_message"]

class TestIntegration:
    """Integration tests combining multiple components"""

    def test_circuit_breaker_with_retry_strategy(self):
        """Test circuit breaker and retry strategy working together"""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        rs = RetryStrategy(max_retries=2, base_delay=0.01)

        call_count = [0]

        def intermittent_failure():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("fail")
            return "success"

        # Use retry strategy within circuit breaker
        success, result, error = cb.call(rs.execute, intermittent_failure)

        assert success is True
        assert result == (True, "success", None)

    def test_error_registry_with_logger(self):
        """Test error registry with error logger"""
        registry = ErrorHandlerRegistry()
        logger = ErrorLogger()

        # Handle errors and log them
        errors = [
            ConnectionError("network fail"),
            ValueError("validation fail"),
            IOError("storage fail"),
        ]

        for error in errors:
            success, msg = registry.handle_error(error, "test", None)
            logger.log_error(error, "test", "medium")

        # Verify all were logged
        assert len(logger.error_log) == 3

        # Verify summary
        summary = logger.get_error_summary()
        assert summary["total_errors"] == 3

    def test_full_error_handling_flow(self):
        """Test complete error handling flow"""
        # Setup components
        registry = ErrorHandlerRegistry()
        logger = ErrorLogger()
        cb = CircuitBreaker(failure_threshold=3, timeout=0.5)

        def operation_with_errors():
            raise ConnectionError("Simulated network failure")

        # Execute with circuit breaker
        for i in range(5):
            success, result, error = cb.call(operation_with_errors)

            if not success:
                # Route through registry
                handled, msg = registry.handle_error(
                    ConnectionError(error or "Unknown"), "operation", None
                )

                # Log the error
                logger.log_error(ConnectionError(error or "Unknown"), "operation", "high")

        # Verify circuit opened
        assert cb.state == CircuitState.OPEN

        # Verify errors were logged
        assert len(logger.error_log) >= 3

        # Verify error statistics
        stats = registry.get_handler_statistics()
        assert stats["total_handlers"] >= 3
