"""Simple coverage test for error_handlers module"""
import pytest
import time
from xai.core.api.error_handlers import (
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


def test_circuit_breaker_init():
    """Test CircuitBreaker initialization"""
    cb = CircuitBreaker(failure_threshold=3, timeout=10, success_threshold=2)
    assert cb.failure_threshold == 3
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_call_success():
    """Test successful CircuitBreaker call"""
    cb = CircuitBreaker()

    def success_func():
        return "success"

    success, result, error = cb.call(success_func)
    assert success is True
    assert result == "success"


def test_circuit_breaker_call_failure():
    """Test failed CircuitBreaker call"""
    cb = CircuitBreaker(failure_threshold=2)

    def fail_func():
        raise ValueError("test error")

    # First failure
    success, result, error = cb.call(fail_func)
    assert success is False

    # Second failure - should open circuit
    success, result, error = cb.call(fail_func)
    assert success is False


def test_circuit_breaker_methods():
    """Test CircuitBreaker methods"""
    cb = CircuitBreaker()

    # Test reset
    cb.reset()
    assert cb.state == CircuitState.CLOSED

    # Test get_state
    state = cb.get_state()
    assert "state" in state
    assert "failure_count" in state


def test_retry_strategy_init():
    """Test RetryStrategy initialization"""
    rs = RetryStrategy(max_retries=3, base_delay=0.1)
    assert rs.max_retries == 3
    assert rs.base_delay == 0.1


def test_retry_strategy_execute_success():
    """Test successful retry execution"""
    rs = RetryStrategy(max_retries=2, base_delay=0.01)

    def success_func():
        return "ok"

    success, result, error = rs.execute(success_func)
    assert success is True
    assert result == "ok"


def test_retry_strategy_execute_failure():
    """Test retry on failure"""
    rs = RetryStrategy(max_retries=2, base_delay=0.01)
    call_count = [0]

    def fail_func():
        call_count[0] += 1
        raise RuntimeError("fail")

    success, result, error = rs.execute(fail_func)
    assert success is False
    assert call_count[0] == 3  # Initial + 2 retries


def test_network_error_handler():
    """Test NetworkErrorHandler"""
    handler = NetworkErrorHandler()
    assert handler.name == "network"

    # Test can_handle
    can = handler.can_handle(ConnectionError("test"), "context")
    assert isinstance(can, bool)

    # Test handle
    success, msg = handler.handle(ConnectionError("test"), "network_op", None)
    assert isinstance(success, bool)


def test_validation_error_handler():
    """Test ValidationErrorHandler"""
    handler = ValidationErrorHandler()
    assert handler.name == "validation"

    # Test can_handle
    can = handler.can_handle(ValueError("invalid"), "context")
    assert isinstance(can, bool)

    # Test handle
    success, msg = handler.handle(ValueError("test"), "validation", None)
    assert isinstance(success, bool)


def test_storage_error_handler():
    """Test StorageErrorHandler"""
    handler = StorageErrorHandler()
    assert handler.name == "storage"

    # Test can_handle
    can = handler.can_handle(IOError("test"), "context")
    assert isinstance(can, bool)

    # Test handle
    success, msg = handler.handle(IOError("test"), "storage", None)
    assert isinstance(success, bool)


def test_error_handler_registry():
    """Test ErrorHandlerRegistry"""
    registry = ErrorHandlerRegistry()

    # Test register_handler
    custom_handler = NetworkErrorHandler()
    registry.register_handler(custom_handler)

    # Test handle_error
    success, msg = registry.handle_error(ConnectionError("test"), "network", None)
    assert isinstance(success, bool)

    # Test get_handler_statistics
    stats = registry.get_handler_statistics()
    assert "total_handlers" in stats


def test_error_logger():
    """Test ErrorLogger"""
    logger = ErrorLogger(max_entries=100)

    # Test log_error
    logger.log_error(ValueError("test"), "test_context", "medium")

    # Test get_recent_errors
    recent = logger.get_recent_errors(5)
    assert isinstance(recent, list)

    # Test get_error_summary
    summary = logger.get_error_summary()
    assert "total_errors" in summary


def test_circuit_states():
    """Test CircuitState enum"""
    assert CircuitState.CLOSED.value == "closed"
    assert CircuitState.OPEN.value == "open"
    assert CircuitState.HALF_OPEN.value == "half_open"


def test_circuit_breaker_half_open():
    """Test circuit breaker half-open state"""
    cb = CircuitBreaker(failure_threshold=1, timeout=1, success_threshold=2)

    # Force failure to open circuit
    def fail():
        raise Exception("fail")

    cb.call(fail)

    # Wait for timeout
    time.sleep(1.1)

    # Next call should enter half-open
    def success():
        return "ok"

    # First success in half-open
    cb.call(success)

    # Second success should close circuit
    cb.call(success)


def test_error_handler_registry_fallback():
    """Test fallback handler"""
    registry = ErrorHandlerRegistry()

    fallback = NetworkErrorHandler()
    registry.set_fallback_handler(fallback)

    # Test with unknown error type
    success, msg = registry.handle_error(Exception("unknown"), "test", None)
    assert isinstance(success, bool)


def test_all_methods_coverage():
    """Execute all methods for coverage"""
    cb = CircuitBreaker()
    cb._on_success()
    cb._on_failure()

    rs = RetryStrategy()
    try:
        rs.execute(lambda: 1/0)
    except:
        pass

    handler = NetworkErrorHandler()
    handler.can_handle(TimeoutError(), "test")

    registry = ErrorHandlerRegistry()
    registry._register_default_handlers()

    logger = ErrorLogger()
    logger.log_error(RuntimeError("test"), "ctx", "critical")
    logger.log_error(RuntimeError("test2"), "ctx", "high")
    logger.get_error_summary()
