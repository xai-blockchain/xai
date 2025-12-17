import logging
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger("xai.security.circuit_breaker")


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"  # Operations proceed normally
    OPEN = "OPEN"  # Operations are blocked
    HALF_OPEN = "HALF_OPEN"  # A limited number of operations are allowed to test recovery


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 300,
        half_open_test_limit: int = 1,
    ):
        if not name:
            raise ValueError("Circuit breaker name cannot be empty.")
        if not isinstance(failure_threshold, int) or failure_threshold <= 0:
            raise ValueError("Failure threshold must be a positive integer.")
        if not isinstance(recovery_timeout_seconds, int) or recovery_timeout_seconds <= 0:
            raise ValueError("Recovery timeout must be a positive integer.")
        if not isinstance(half_open_test_limit, int) or half_open_test_limit <= 0:
            raise ValueError("Half-open test limit must be a positive integer.")

        self.name = name
        self._state = CircuitBreakerState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_test_limit = half_open_test_limit

        self._failure_count = 0
        self._last_trip_timestamp: int = 0
        self._half_open_attempts = 0  # Tracks requests/successes in half-open state

        logger.info("Circuit breaker %s initialized in %s state", self.name, self._state.value)

    @property
    def state(self) -> CircuitBreakerState:
        # Automatically transition from OPEN to HALF_OPEN after timeout
        if self._state == CircuitBreakerState.OPEN:
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            if current_timestamp >= self._last_trip_timestamp + self.recovery_timeout_seconds:
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_attempts = 0
                logger.info(
                    "Circuit breaker %s transitioned to %s (recovery timeout)",
                    self.name,
                    self._state.value,
                )
        return self._state

    def _transition_to_open(self):
        self._state = CircuitBreakerState.OPEN
        self._last_trip_timestamp = int(datetime.now(timezone.utc).timestamp())
        self._failure_count = 0  # Reset failure count when opening
        self._half_open_attempts = 0  # Reset half-open attempts when opening
        logger.warning("Circuit breaker %s tripped to %s", self.name, self._state.value)

    def _transition_to_closed(self):
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0
        logger.info("Circuit breaker %s reset to %s", self.name, self._state.value)

    def _transition_to_half_open(self):
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_attempts = 0
        logger.info("Circuit breaker %s transitioned to %s", self.name, self._state.value)

    def record_failure(self):
        if self.state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            logger.warning(
                "Circuit breaker %s failure recorded (%d/%d)",
                self.name,
                self._failure_count,
                self.failure_threshold,
            )
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # If a failure occurs in HALF_OPEN, immediately go back to OPEN
            self._transition_to_open()
        # No action if already OPEN

    def record_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_attempts += 1
            logger.info(
                "Circuit breaker %s success recorded in HALF_OPEN (%d/%d)",
                self.name,
                self._half_open_attempts,
                self.half_open_test_limit,
            )
            if self._half_open_attempts >= self.half_open_test_limit:
                self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            self._failure_count = 0  # Reset failure count on success in CLOSED state
        # No action if OPEN

    def allow_request(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            logger.warning("Circuit breaker %s is OPEN. Request blocked", self.name)
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow a limited number of requests in HALF_OPEN state
            # Increment counter when allowing a request
            if self._half_open_attempts < self.half_open_test_limit:
                self._half_open_attempts += 1
                logger.info(
                    "Circuit breaker %s is HALF_OPEN. Allowing test request %d/%d",
                    self.name,
                    self._half_open_attempts,
                    self.half_open_test_limit,
                )
                return True
            else:
                logger.warning(
                    "Circuit breaker %s is HALF_OPEN and test limit reached. Request blocked",
                    self.name,
                )
                return False
        else:  # CLOSED
            return True

    def reset(self):
        """Manually reset circuit to CLOSED state."""
        self._transition_to_closed()

    def force_open(self):
        """Manually trip the circuit breaker regardless of thresholds."""
        self._transition_to_open()

    def snapshot(self) -> dict:
        """Return a serializable snapshot of the breaker state for APIs."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "half_open_test_limit": self.half_open_test_limit,
        }
