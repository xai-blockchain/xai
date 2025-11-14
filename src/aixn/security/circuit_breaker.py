from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"       # Operations proceed normally
    OPEN = "OPEN"           # Operations are blocked
    HALF_OPEN = "HALF_OPEN" # A limited number of operations are allowed to test recovery

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout_seconds: int = 300,
                 half_open_test_limit: int = 1):
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
        self._half_open_attempts = 0

        print(f"Circuit Breaker '{self.name}' initialized in {self._state.value} state.")

    @property
    def state(self) -> CircuitBreakerState:
        # Automatically transition from OPEN to HALF_OPEN after timeout
        if self._state == CircuitBreakerState.OPEN:
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            if current_timestamp >= self._last_trip_timestamp + self.recovery_timeout_seconds:
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_attempts = 0
                print(f"Circuit Breaker '{self.name}' transitioned to {self._state.value} state (recovery timeout).")
        return self._state

    def _transition_to_open(self):
        self._state = CircuitBreakerState.OPEN
        self._last_trip_timestamp = int(datetime.now(timezone.utc).timestamp())
        self._failure_count = 0 # Reset failure count when opening
        print(f"Circuit Breaker '{self.name}' TRIPPED to {self._state.value} state.")

    def _transition_to_closed(self):
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0
        print(f"Circuit Breaker '{self.name}' RESET to {self._state.value} state.")

    def _transition_to_half_open(self):
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_attempts = 0
        print(f"Circuit Breaker '{self.name}' transitioned to {self._state.value} state.")

    def record_failure(self):
        if self.state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            print(f"Circuit Breaker '{self.name}': Failure recorded. Count: {self._failure_count}/{self.failure_threshold}")
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # If a failure occurs in HALF_OPEN, immediately go back to OPEN
            self._transition_to_open()
        # No action if already OPEN

    def record_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_attempts += 1
            print(f"Circuit Breaker '{self.name}': Success recorded in HALF_OPEN. Attempts: {self._half_open_attempts}/{self.half_open_test_limit}")
            if self._half_open_attempts >= self.half_open_test_limit:
                self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            self._failure_count = 0 # Reset failure count on success in CLOSED state
        # No action if OPEN

    def allow_request(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            print(f"Circuit Breaker '{self.name}' is OPEN. Request BLOCKED.")
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow a limited number of requests in HALF_OPEN
            if self._half_open_attempts < self.half_open_test_limit:
                print(f"Circuit Breaker '{self.name}' is HALF_OPEN. Allowing test request.")
                return True
            else:
                print(f"Circuit Breaker '{self.name}' is HALF_OPEN, test limit reached. Request BLOCKED.")
                return False
        else: # CLOSED
            return True

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Circuit breaker for bridge transfers
    bridge_cb = CircuitBreaker(name="BridgeTransferCB", failure_threshold=2, recovery_timeout_seconds=5, half_open_test_limit=1)

    print("\n--- Initial state (CLOSED) ---")
    if bridge_cb.allow_request():
        print("Bridge transfer 1 allowed.")
        bridge_cb.record_success() # Keep it closed
    
    print("\n--- Simulating failures ---")
    if bridge_cb.allow_request():
        print("Bridge transfer 2 allowed.")
        bridge_cb.record_failure() # 1st failure
    
    if bridge_cb.allow_request():
        print("Bridge transfer 3 allowed.")
        bridge_cb.record_failure() # 2nd failure
    
    if bridge_cb.allow_request():
        print("Bridge transfer 4 allowed.")
        bridge_cb.record_failure() # 3rd failure, should trip to OPEN
    
    print("\n--- State after tripping (OPEN) ---")
    if not bridge_cb.allow_request():
        print("Bridge transfer 5 BLOCKED (as expected).")
    
    print("\n--- Waiting for recovery timeout ---")
    import time
    time.sleep(6) # Wait for 5 seconds + a bit

    print("\n--- State after timeout (HALF_OPEN) ---")
    if bridge_cb.allow_request():
        print("Bridge transfer 6 allowed (HALF_OPEN test).")
        bridge_cb.record_success() # Success in HALF_OPEN, should close
    
    print("\n--- State after successful test (CLOSED) ---")
    if bridge_cb.allow_request():
        print("Bridge transfer 7 allowed (circuit closed).")
        bridge_cb.record_success()

    print("\n--- Simulating failure in HALF_OPEN ---")
    bridge_cb.record_failure() # 1st failure
    bridge_cb.record_failure() # 2nd failure
    bridge_cb.record_failure() # 3rd failure, trips to OPEN
    
    time.sleep(6) # Wait for timeout
    
    if bridge_cb.allow_request():
        print("Bridge transfer 8 allowed (HALF_OPEN test).")
        bridge_cb.record_failure() # Failure in HALF_OPEN, should immediately open again
    
    if not bridge_cb.allow_request():
        print("Bridge transfer 9 BLOCKED (as expected, immediately re-opened).")
