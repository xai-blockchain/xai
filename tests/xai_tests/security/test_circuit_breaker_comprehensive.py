"""
Comprehensive tests for Circuit Breaker security module.

Tests all states (CLOSED, OPEN, HALF_OPEN), state transitions,
failure tracking, success tracking, recovery timeouts, and edge cases.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


class TestCircuitBreakerInitialization:
    """Test circuit breaker initialization and configuration"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        cb = CircuitBreaker(name="TestCB")
        assert cb.name == "TestCB"
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout_seconds == 300
        assert cb.half_open_test_limit == 1
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._failure_count == 0
        assert cb._half_open_attempts == 0

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters"""
        cb = CircuitBreaker(
            name="CustomCB",
            failure_threshold=5,
            recovery_timeout_seconds=60,
            half_open_test_limit=3
        )
        assert cb.name == "CustomCB"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout_seconds == 60
        assert cb.half_open_test_limit == 3

    def test_init_empty_name_raises_error(self):
        """Test that empty name raises ValueError"""
        with pytest.raises(ValueError, match="Circuit breaker name cannot be empty"):
            CircuitBreaker(name="")

    def test_init_invalid_failure_threshold(self):
        """Test that invalid failure threshold raises ValueError"""
        with pytest.raises(ValueError, match="Failure threshold must be a positive integer"):
            CircuitBreaker(name="Test", failure_threshold=0)

        with pytest.raises(ValueError, match="Failure threshold must be a positive integer"):
            CircuitBreaker(name="Test", failure_threshold=-1)

        with pytest.raises(ValueError, match="Failure threshold must be a positive integer"):
            CircuitBreaker(name="Test", failure_threshold=3.5)

    def test_init_invalid_recovery_timeout(self):
        """Test that invalid recovery timeout raises ValueError"""
        with pytest.raises(ValueError, match="Recovery timeout must be a positive integer"):
            CircuitBreaker(name="Test", recovery_timeout_seconds=0)

        with pytest.raises(ValueError, match="Recovery timeout must be a positive integer"):
            CircuitBreaker(name="Test", recovery_timeout_seconds=-10)

    def test_init_invalid_half_open_limit(self):
        """Test that invalid half-open test limit raises ValueError"""
        with pytest.raises(ValueError, match="Half-open test limit must be a positive integer"):
            CircuitBreaker(name="Test", half_open_test_limit=0)

        with pytest.raises(ValueError, match="Half-open test limit must be a positive integer"):
            CircuitBreaker(name="Test", half_open_test_limit=-5)


class TestCircuitBreakerClosedState:
    """Test circuit breaker behavior in CLOSED state"""

    def test_closed_state_allows_requests(self):
        """Test that CLOSED state allows requests"""
        cb = CircuitBreaker(name="TestCB")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.allow_request() is True

    def test_closed_state_multiple_requests(self):
        """Test that CLOSED state allows multiple requests"""
        cb = CircuitBreaker(name="TestCB")
        for _ in range(10):
            assert cb.allow_request() is True

    def test_record_success_resets_failure_count(self):
        """Test that success in CLOSED state resets failure count"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2
        cb.record_success()
        assert cb._failure_count == 0

    def test_record_failure_increments_count(self):
        """Test that failure increments failure count"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=5)
        assert cb._failure_count == 0
        cb.record_failure()
        assert cb._failure_count == 1
        cb.record_failure()
        assert cb._failure_count == 2

    def test_failure_threshold_triggers_open(self):
        """Test that reaching failure threshold transitions to OPEN"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_failure_count_resets_on_open(self):
        """Test that failure count resets when transitioning to OPEN"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb._failure_count == 0


class TestCircuitBreakerOpenState:
    """Test circuit breaker behavior in OPEN state"""

    def test_open_state_blocks_requests(self):
        """Test that OPEN state blocks requests"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

    def test_open_state_blocks_multiple_requests(self):
        """Test that OPEN state blocks multiple consecutive requests"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=1)
        cb.record_failure()
        for _ in range(10):
            assert cb.allow_request() is False

    def test_record_failure_in_open_has_no_effect(self):
        """Test that recording failure in OPEN state has no effect"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_record_success_in_open_has_no_effect(self):
        """Test that recording success in OPEN state has no effect"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.OPEN

    def test_automatic_transition_to_half_open(self):
        """Test automatic transition from OPEN to HALF_OPEN after timeout"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=1, recovery_timeout_seconds=1)
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_last_trip_timestamp_set_on_open(self):
        """Test that last trip timestamp is set when transitioning to OPEN"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=2)
        before = int(datetime.now(timezone.utc).timestamp())
        cb.record_failure()
        cb.record_failure()
        after = int(datetime.now(timezone.utc).timestamp())
        assert before <= cb._last_trip_timestamp <= after


class TestCircuitBreakerHalfOpenState:
    """Test circuit breaker behavior in HALF_OPEN state"""

    def test_half_open_allows_limited_requests(self):
        """Test that HALF_OPEN allows limited number of test requests"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=3
        )
        cb.record_failure()
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Should allow up to test limit
        assert cb.allow_request() is True
        assert cb.allow_request() is True
        assert cb.allow_request() is True
        # Beyond limit should be blocked
        assert cb.allow_request() is False

    def test_half_open_success_transitions_to_closed(self):
        """Test that sufficient successes in HALF_OPEN transition to CLOSED"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=2
        )
        cb.record_failure()
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_returns_to_open(self):
        """Test that failure in HALF_OPEN immediately returns to OPEN"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=2,
            recovery_timeout_seconds=1,
            half_open_test_limit=3
        )
        cb.record_failure()
        cb.record_failure()
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_half_open_attempts_reset_on_failure(self):
        """Test that half-open attempts reset when returning to OPEN"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=2
        )
        cb.record_failure()
        time.sleep(1.1)

        cb.record_success()
        assert cb._half_open_attempts == 1
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb._half_open_attempts == 0

    def test_half_open_attempts_reset_on_closed(self):
        """Test that half-open attempts reset when transitioning to CLOSED"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=2
        )
        cb.record_failure()
        time.sleep(1.1)

        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._half_open_attempts == 0

    def test_half_open_single_success_limit(self):
        """Test HALF_OPEN with single success requirement"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )
        cb.record_failure()
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerStateTransitions:
    """Test various state transition scenarios"""

    def test_closed_to_open_to_half_open_to_closed(self):
        """Test complete recovery cycle"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=2,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )

        # CLOSED -> OPEN
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # OPEN -> HALF_OPEN
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # HALF_OPEN -> CLOSED
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_to_open_to_half_open_cycle(self):
        """Test repeated HALF_OPEN failures"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )

        # Trip to OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # First recovery attempt fails
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Second recovery attempt succeeds
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_multiple_failures_in_closed_before_threshold(self):
        """Test that failures below threshold keep circuit CLOSED"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=5)

        for i in range(4):
            cb.record_failure()
            assert cb.state == CircuitBreakerState.CLOSED
            assert cb._failure_count == i + 1


class TestCircuitBreakerEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_recovery_timeout_invalid(self):
        """Test that zero recovery timeout is rejected"""
        with pytest.raises(ValueError):
            CircuitBreaker(name="Test", recovery_timeout_seconds=0)

    def test_single_failure_threshold(self):
        """Test circuit breaker with threshold of 1"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_high_failure_threshold(self):
        """Test circuit breaker with high threshold"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=100)
        for i in range(99):
            cb.record_failure()
            assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_rapid_state_transitions(self):
        """Test rapid state transitions"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )

        # Rapid cycling
        for _ in range(3):
            cb.record_failure()
            assert cb.state == CircuitBreakerState.OPEN
            time.sleep(1.1)
            assert cb.state == CircuitBreakerState.HALF_OPEN
            cb.record_success()
            assert cb.state == CircuitBreakerState.CLOSED

    def test_concurrent_success_and_failure_recording(self):
        """Test mixed success and failure recording"""
        cb = CircuitBreaker(name="TestCB", failure_threshold=5)

        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0

        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED

    def test_state_property_checks_timeout_each_call(self):
        """Test that state property checks timeout on each access"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1
        )

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Multiple state checks before timeout
        for _ in range(5):
            assert cb.state == CircuitBreakerState.OPEN
            time.sleep(0.1)

        # After timeout - add buffer for execution overhead
        time.sleep(0.7)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_large_half_open_test_limit(self):
        """Test HALF_OPEN with large test limit"""
        cb = CircuitBreaker(
            name="TestCB",
            failure_threshold=1,
            recovery_timeout_seconds=1,
            half_open_test_limit=10
        )

        cb.record_failure()
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Record 9 successes
        for i in range(9):
            cb.record_success()
            assert cb.state == CircuitBreakerState.HALF_OPEN
            assert cb._half_open_attempts == i + 1

        # 10th success should close
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerUseCases:
    """Test real-world use case scenarios"""

    def test_api_rate_limiting_scenario(self):
        """Test circuit breaker for API rate limiting"""
        api_cb = CircuitBreaker(
            name="API_RateLimit",
            failure_threshold=5,
            recovery_timeout_seconds=2,
            half_open_test_limit=2
        )

        # Simulate 5 failed API calls
        for _ in range(5):
            api_cb.record_failure()

        assert api_cb.state == CircuitBreakerState.OPEN
        assert api_cb.allow_request() is False

        # Wait for recovery
        time.sleep(2.1)
        assert api_cb.state == CircuitBreakerState.HALF_OPEN

        # Test with 2 successful calls
        assert api_cb.allow_request() is True
        api_cb.record_success()
        assert api_cb.allow_request() is True
        api_cb.record_success()

        assert api_cb.state == CircuitBreakerState.CLOSED

    def test_database_connection_scenario(self):
        """Test circuit breaker for database connection failures"""
        db_cb = CircuitBreaker(
            name="DB_Connection",
            failure_threshold=3,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )

        # Simulate database connection failures
        for i in range(3):
            if db_cb.allow_request():
                db_cb.record_failure()

        assert db_cb.state == CircuitBreakerState.OPEN

        # Wait and retry
        time.sleep(1.1)
        if db_cb.allow_request():
            db_cb.record_success()

        assert db_cb.state == CircuitBreakerState.CLOSED

    def test_bridge_transfer_scenario(self):
        """Test circuit breaker for blockchain bridge transfers"""
        bridge_cb = CircuitBreaker(
            name="BridgeTransfer",
            failure_threshold=2,
            recovery_timeout_seconds=1,
            half_open_test_limit=1
        )

        # Successful transfer
        assert bridge_cb.allow_request()
        bridge_cb.record_success()

        # Two failed transfers
        assert bridge_cb.allow_request()
        bridge_cb.record_failure()
        assert bridge_cb.allow_request()
        bridge_cb.record_failure()

        # Circuit should be open
        assert bridge_cb.state == CircuitBreakerState.OPEN
        assert bridge_cb.allow_request() is False

        # Recovery
        time.sleep(1.1)
        assert bridge_cb.state == CircuitBreakerState.HALF_OPEN
        if bridge_cb.allow_request():
            bridge_cb.record_success()

        assert bridge_cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerNameValidation:
    """Test circuit breaker name handling"""

    def test_name_with_special_characters(self):
        """Test circuit breaker with special characters in name"""
        cb = CircuitBreaker(name="API_v2.0-Production")
        assert cb.name == "API_v2.0-Production"

    def test_name_with_spaces(self):
        """Test circuit breaker with spaces in name"""
        cb = CircuitBreaker(name="Bridge Transfer CB")
        assert cb.name == "Bridge Transfer CB"

    def test_name_with_unicode(self):
        """Test circuit breaker with unicode characters in name"""
        cb = CircuitBreaker(name="API_测试")
        assert cb.name == "API_测试"

    def test_very_long_name(self):
        """Test circuit breaker with very long name"""
        long_name = "A" * 1000
        cb = CircuitBreaker(name=long_name)
        assert cb.name == long_name
