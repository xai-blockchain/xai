from typing import Dict, Any
from datetime import datetime, timezone
from src.aixn.security.circuit_breaker import CircuitBreaker, CircuitBreakerState # Import CircuitBreaker

class EmergencyPauseManager:
    def __init__(self, authorized_pauser_address: str, circuit_breaker: CircuitBreaker = None):
        if not authorized_pauser_address:
            raise ValueError("Authorized pauser address cannot be empty.")
        
        self.authorized_pauser_address = authorized_pauser_address
        self._is_paused = False
        self.paused_by = None
        self.paused_timestamp = None
        self.reason = None
        self.circuit_breaker = circuit_breaker # Optional: for automatic pausing

    def pause_operations(self, caller_address: str, reason: str = "Manual emergency pause"):
        if caller_address != self.authorized_pauser_address:
            raise PermissionError(f"Caller {caller_address} is not authorized to pause operations.")
        
        if not self._is_paused:
            self._is_paused = True
            self.paused_by = caller_address
            self.paused_timestamp = int(datetime.now(timezone.utc).timestamp())
            self.reason = reason
            print(f"!!! EMERGENCY PAUSE ACTIVATED !!! Reason: {reason} (by {caller_address})")
        else:
            print("Operations are already paused.")

    def unpause_operations(self, caller_address: str, reason: str = "Manual unpause"):
        if caller_address != self.authorized_pauser_address:
            raise PermissionError(f"Caller {caller_address} is not authorized to unpause operations.")
        
        if self._is_paused:
            self._is_paused = False
            self.paused_by = None
            self.paused_timestamp = None
            self.reason = None
            print(f"--- Operations UNPAUSED --- Reason: {reason} (by {caller_address})")
        else:
            print("Operations are not currently paused.")

    def check_and_auto_pause(self):
        """
        Checks the associated circuit breaker and automatically pauses if it's OPEN.
        """
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            if not self._is_paused:
                self.pause_operations(
                    caller_address="0xAutomatedSystem", # Automated system as caller
                    reason=f"Automatic pause triggered by Circuit Breaker '{self.circuit_breaker.name}' due to anomalies."
                )
            else:
                print(f"Circuit Breaker '{self.circuit_breaker.name}' is OPEN, but operations already paused.")
        elif self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.CLOSED and self._is_paused and self.paused_by == "0xAutomatedSystem":
            # If circuit breaker recovers and pause was automated, unpause
            self.unpause_operations(
                caller_address="0xAutomatedSystem",
                reason=f"Automatic unpause as Circuit Breaker '{self.circuit_breaker.name}' recovered."
            )


    def is_paused(self) -> bool:
        # Also check circuit breaker state if available
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            return True
        return self._is_paused

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_paused": self.is_paused(),
            "paused_by": self.paused_by,
            "paused_timestamp": self.paused_timestamp,
            "reason": self.reason,
            "circuit_breaker_state": self.circuit_breaker.state.value if self.circuit_breaker else "N/A"
        }

# Example Usage (for testing purposes)
if __name__ == "__main__":
    AUTHORIZED_ADMIN = "0xAdminMultiSig"
    
    # Initialize a Circuit Breaker for demonstration
    bridge_cb = CircuitBreaker(name="BridgeAnomalyDetector", failure_threshold=2, recovery_timeout_seconds=5)
    
    pause_manager = EmergencyPauseManager(AUTHORIZED_ADMIN, circuit_breaker=bridge_cb)

    print("--- Initial Status ---")
    print(pause_manager.get_status())

    print("\n--- Unauthorized Pause Attempt ---")
    try:
        pause_manager.pause_operations("0xUnauthorizedUser", "Just testing")
    except PermissionError as e:
        print(f"Error (expected): {e}")

    print("\n--- Authorized Manual Pause ---")
    pause_manager.pause_operations(AUTHORIZED_ADMIN, "Critical vulnerability detected in bridge contract.")
    print(pause_manager.get_status())

    print("\n--- Attempting operation while paused ---")
    if not pause_manager.is_paused():
        print("Bridge operation allowed.")
    else:
        print("Bridge operation BLOCKED due to pause.")

    print("\n--- Authorized Manual Unpause ---")
    pause_manager.unpause_operations(AUTHORIZED_ADMIN, "Vulnerability patched and verified.")
    print(pause_manager.get_status())

    print("\n--- Simulating Circuit Breaker Trip and Auto-Pause ---")
    bridge_cb.record_failure()
    bridge_cb.record_failure() # This should trip the circuit breaker to OPEN
    bridge_cb.record_failure() # Another failure to ensure it stays open

    pause_manager.check_and_auto_pause() # Manager should detect OPEN CB and pause
    print(pause_manager.get_status())

    print("\n--- Waiting for Circuit Breaker recovery timeout ---")
    import time
    time.sleep(6) # Wait for 5 seconds + a bit

    print("\n--- Checking status after CB timeout (should be HALF_OPEN, then auto-unpause) ---")
    # Simulate a successful operation through the HALF_OPEN circuit breaker
    if bridge_cb.allow_request():
        bridge_cb.record_success() # This should transition CB to CLOSED
    
    pause_manager.check_and_auto_pause() # Manager should detect CLOSED CB and unpause
    print(pause_manager.get_status())
