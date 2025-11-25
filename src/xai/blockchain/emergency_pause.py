import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from ..security.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger("xai.blockchain.emergency_pause")


AUTOMATED_CALLER = "0xAutomatedSystem"


class EmergencyPauseManager:
    def __init__(
        self,
        authorized_pauser_address: str,
        circuit_breaker: Optional[CircuitBreaker] = None,
        time_provider: Optional[Callable[[], int]] = None,
    ):
        if not authorized_pauser_address:
            raise ValueError("Authorized pauser address cannot be empty.")

        self.authorized_pauser_address = authorized_pauser_address
        self._is_paused = False
        self.paused_by = None
        self.paused_timestamp = None
        self.reason = None
        self.circuit_breaker = circuit_breaker  # Optional: for automatic pausing
        self._time_provider = time_provider or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def pause_operations(self, caller_address: str, reason: str = "Manual emergency pause"):
        if caller_address not in (self.authorized_pauser_address, AUTOMATED_CALLER):
            raise PermissionError(f"Caller {caller_address} is not authorized to pause operations.")

        if not self._is_paused:
            self._is_paused = True
            self.paused_by = caller_address
            self.paused_timestamp = self._current_timestamp()
            self.reason = reason
            logger.warning("Emergency pause activated by %s. Reason: %s", caller_address, reason)
        else:
            logger.info("Pause requested but operations already paused.")

    def unpause_operations(self, caller_address: str, reason: str = "Manual unpause"):
        if caller_address not in (self.authorized_pauser_address, AUTOMATED_CALLER):
            raise PermissionError(
                f"Caller {caller_address} is not authorized to unpause operations."
            )

        if self._is_paused:
            self._is_paused = False
            self.paused_by = None
            self.paused_timestamp = None
            self.reason = None
            logger.info("Operations unpaused by %s. Reason: %s", caller_address, reason)
        else:
            logger.info("Unpause requested but operations not paused.")

    def check_and_auto_pause(self):
        """
        Checks the associated circuit breaker and automatically pauses if it's OPEN.
        """
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            if not self._is_paused:
                self.pause_operations(
                    caller_address=AUTOMATED_CALLER,
                    reason=f"Automatic pause triggered by Circuit Breaker '{self.circuit_breaker.name}' due to anomalies.",
                )
            else:
                logger.debug(
                    "Circuit breaker %s OPEN but operations already paused", self.circuit_breaker.name
                )
        elif (
            self.circuit_breaker
            and self.circuit_breaker.state == CircuitBreakerState.CLOSED
            and self._is_paused
            and self.paused_by == AUTOMATED_CALLER
        ):
            # If circuit breaker recovers and pause was automated, unpause
            self.unpause_operations(
                caller_address=AUTOMATED_CALLER,
                reason=f"Automatic unpause as Circuit Breaker '{self.circuit_breaker.name}' recovered.",
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
            "circuit_breaker_state": (
                self.circuit_breaker.state.value if self.circuit_breaker else "N/A"
            ),
        }

    def _current_timestamp(self) -> int:
        return int(self._time_provider())
