# src/xai/blockchain/emergency_pause.py
"""
Manages the emergency pause functionality for the blockchain, with persistent state.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..database.storage_manager import StorageManager
from ..security.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger("xai.blockchain.emergency_pause")


AUTOMATED_CALLER = "0xAutomatedSystem"
STATE_KEY = "emergency_pause_state"


class EmergencyPauseManager:
    """
    Manages the emergency pause state of the blockchain, persisting the state
    to a database to ensure durability across node restarts.
    """

    def __init__(
        self,
        authorized_pauser_address: str,
        db_path: Optional[Path] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        time_provider: Optional[Callable[[], int]] = None,
    ):
        if not authorized_pauser_address:
            raise ValueError("Authorized pauser address cannot be empty.")

        storage_path = db_path or Path.home() / ".xai" / "emergency_pause.db"
        self.storage = StorageManager(storage_path)
        self.authorized_pauser_address = authorized_pauser_address
        self.circuit_breaker = circuit_breaker  # Optional: for automatic pausing
        self._time_provider = time_provider or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def _get_state(self) -> Dict[str, Any]:
        """Retrieves the pause state from the database."""
        default_state = {
            "is_paused": False,
            "paused_by": None,
            "paused_timestamp": None,
            "reason": None,
        }
        return self.storage.get(STATE_KEY, default=default_state)

    def _set_state(self, state: Dict[str, Any]):
        """Saves the pause state to the database."""
        self.storage.set(STATE_KEY, state)

    def pause_operations(self, caller_address: str, reason: str = "Manual emergency pause"):
        """Pauses operations if the caller is authorized and the system is not already paused."""
        if caller_address not in (self.authorized_pauser_address, AUTOMATED_CALLER):
            raise PermissionError(f"Caller {caller_address} is not authorized to pause operations.")

        state = self._get_state()
        if not state["is_paused"]:
            new_state = {
                "is_paused": True,
                "paused_by": caller_address,
                "paused_timestamp": self._current_timestamp(),
                "reason": reason,
            }
            self._set_state(new_state)
            logger.warning("Emergency pause activated by %s. Reason: %s", caller_address, reason)
        else:
            logger.info("Pause requested but operations already paused.")

    def unpause_operations(self, caller_address: str, reason: str = "Manual unpause"):
        """Unpauses operations if the caller is authorized and the system is paused."""
        if caller_address not in (self.authorized_pauser_address, AUTOMATED_CALLER):
            raise PermissionError(
                f"Caller {caller_address} is not authorized to unpause operations."
            )

        state = self._get_state()
        if state["is_paused"]:
            new_state = {
                "is_paused": False,
                "paused_by": None,
                "paused_timestamp": None,
                "reason": None,
            }
            self._set_state(new_state)
            logger.info("Operations unpaused by %s. Reason: %s", caller_address, reason)
        else:
            logger.info("Unpause requested but operations not paused.")

    def check_and_auto_pause(self):
        """
        Checks the associated circuit breaker and automatically pauses or unpauses
        based on its state.
        """
        state = self._get_state()
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            if not state["is_paused"]:
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
            and state["is_paused"]
            and state["paused_by"] == AUTOMATED_CALLER
        ):
            # If circuit breaker recovers and pause was automated, unpause
            self.unpause_operations(
                caller_address=AUTOMATED_CALLER,
                reason=f"Automatic unpause as Circuit Breaker '{self.circuit_breaker.name}' recovered.",
            )

    def is_paused(self) -> bool:
        """
        Checks if operations are currently paused, either manually or by a circuit breaker.
        """
        # Always check circuit breaker first for immediate, non-persistent trips
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            return True
        # Then check the persistent state
        return self._get_state()["is_paused"]

    def get_status(self) -> Dict[str, Any]:
        """
        Returns a dictionary with the current pause status, including data from the
        database and the circuit breaker.
        """
        persistent_state = self._get_state()
        # The `is_paused()` method correctly checks both sources, so we use it
        persistent_state["is_paused"] = self.is_paused()
        persistent_state["circuit_breaker_state"] = (
            self.circuit_breaker.state.value if self.circuit_breaker else "N/A"
        )
        return persistent_state

    def _current_timestamp(self) -> int:
        """Returns the current UTC timestamp as an integer."""
        return int(self._time_provider())

    def close(self):
        """Closes the underlying storage connection."""
        self.storage.close()
