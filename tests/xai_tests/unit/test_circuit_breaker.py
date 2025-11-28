import time

from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


def test_circuit_breaker_trips_and_recovers():
    cb = CircuitBreaker(
        name="test",
        failure_threshold=2,
        recovery_timeout_seconds=1,
        half_open_test_limit=1,
    )
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.allow_request() is True

    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False

    time.sleep(1.1)
    # state property should auto-transition to HALF_OPEN
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.allow_request() is True
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED


def test_half_open_failure_returns_to_open():
    cb = CircuitBreaker(
        name="test-half-open",
        failure_threshold=1,
        recovery_timeout_seconds=1,
        half_open_test_limit=1,
    )
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    time.sleep(1.1)
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False
