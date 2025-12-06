"""
XAI Blockchain - Transaction Nonce Tracking

Prevents replay attacks by tracking sequential nonces per address.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional
from threading import RLock

logger = logging.getLogger(__name__)


class NonceTracker:
    """
    Track transaction nonces per address

    Each address has a sequential nonce starting from 0.
    Transactions must have nonce = current_nonce + 1.
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        """
        Initialize nonce tracker

        Args:
            data_dir: Directory to store nonce data
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.nonce_file = os.path.join(data_dir, "nonces.json")
        self.nonces: Dict[str, int] = {}
        self.pending_nonces: Dict[str, int] = {}
        self.lock = RLock()

        # Load existing nonces
        self._load_nonces()

    def _load_nonces(self) -> None:
        """Load nonces from file"""
        if os.path.exists(self.nonce_file):
            try:
                with open(self.nonce_file, "r") as f:
                    self.nonces = json.load(f)
            except Exception as e:
                logger.warning(
                    "Failed to load nonces from %s: %s - starting fresh",
                    self.nonce_file,
                    type(e).__name__,
                    extra={"event": "nonce.load_failed", "error": str(e)}
                )
                self.nonces = {}

    def _save_nonces(self) -> None:
        """Save nonces to file"""
        try:
            with open(self.nonce_file, "w") as f:
                json.dump(self.nonces, f, indent=2)
        except Exception as e:
            logger.error(
                "Failed to save nonces to %s: %s",
                self.nonce_file,
                type(e).__name__,
                extra={"event": "nonce.save_failed", "error": str(e)}
            )

    def _get_confirmed_nonce(self, address: str) -> int:
        return self.nonces.get(address, -1)

    def _get_effective_nonce(self, address: str) -> int:
        confirmed = self._get_confirmed_nonce(address)
        pending = self.pending_nonces.get(address)
        if pending is not None and pending > confirmed:
            return pending
        return confirmed

    def get_nonce(self, address: str) -> int:
        """
        Get current nonce for address

        Args:
            address: Wallet address

        Returns:
            int: Current nonce (0 if new address)
        """
        with self.lock:
            return self._get_confirmed_nonce(address)

    def get_next_nonce(self, address: str) -> int:
        """
        Get next expected nonce for address

        Args:
            address: Wallet address

        Returns:
            int: Next nonce to use
        """
        with self.lock:
            return self._get_effective_nonce(address) + 1

    def validate_nonce(self, address: str, nonce: int) -> bool:
        """
        Validate that nonce is correct for address

        Args:
            address: Wallet address
            nonce: Proposed nonce

        Returns:
            bool: True if nonce is valid
        """
        with self.lock:
            expected = self._get_effective_nonce(address) + 1
            return nonce == expected

    def reserve_nonce(self, address: str, nonce: int) -> None:
        """
        Track a nonce that has been accepted into the mempool so the next
        transaction from the same address can use nonce+1 even before confirmation.
        """
        with self.lock:
            current = self._get_effective_nonce(address)
            if nonce <= current:
                return
            self.pending_nonces[address] = nonce

    def increment_nonce(self, address: str, nonce: Optional[int] = None) -> None:
        """
        Increment nonce after successful transaction

        Args:
            address: Wallet address
        """
        with self.lock:
            confirmed = self._get_confirmed_nonce(address)
            next_nonce = nonce if nonce is not None else confirmed + 1
            if next_nonce < confirmed:
                next_nonce = confirmed

            self.nonces[address] = next_nonce
            pending = self.pending_nonces.get(address)
            if pending is not None and pending <= next_nonce:
                self.pending_nonces.pop(address, None)

            self._save_nonces()

    def set_nonce(self, address: str, nonce: int) -> None:
        """
        Force-set an address nonce. Used when replaying historical blocks
        (e.g., chain reorganizations or VM state sync).
        """
        if nonce < -1:
            raise ValueError("nonce must be >= -1")

        with self.lock:
            self.nonces[address] = int(nonce)
            pending = self.pending_nonces.get(address)
            if pending is not None and pending <= nonce:
                self.pending_nonces.pop(address, None)
            self._save_nonces()

    def reset(self) -> None:
        """
        Clear all tracked nonces. Used when rebuilding from chain state.
        """
        with self.lock:
            self.nonces.clear()
            self.pending_nonces.clear()
            self._save_nonces()

    def reset_nonce(self, address: str) -> None:
        """
        Reset nonce to 0 (for testing only)

        Args:
            address: Wallet address
        """
        with self.lock:
            self.nonces[address] = -1
            self.pending_nonces.pop(address, None)
            self._save_nonces()

    def get_stats(self) -> dict:
        """
        Get nonce tracking statistics

        Returns:
            dict: Statistics
        """
        with self.lock:
            return {
                "total_addresses": len(self.nonces),
                "highest_nonce": max(self.nonces.values()) if self.nonces else 0,
                "total_transactions": sum(self.nonces.values()),
            }


# Global nonce tracker instance
_global_nonce_tracker = None


def get_nonce_tracker() -> NonceTracker:
    """
    Get global nonce tracker instance

    Returns:
        NonceTracker: Global tracker
    """
    global _global_nonce_tracker
    if _global_nonce_tracker is None:
        _global_nonce_tracker = NonceTracker()
    return _global_nonce_tracker


def validate_transaction_nonce(address: str, nonce: int) -> bool:
    """
    Convenience function to validate nonce

    Args:
        address: Wallet address
        nonce: Proposed nonce

    Returns:
        bool: True if valid
    """
    tracker = get_nonce_tracker()
    return tracker.validate_nonce(address, nonce)


def increment_transaction_nonce(address: str, nonce: Optional[int] = None) -> None:
    """
    Convenience function to increment nonce

    Args:
        address: Wallet address
    """
    tracker = get_nonce_tracker()
    tracker.increment_nonce(address, nonce)


def get_next_nonce(address: str) -> int:
    """
    Convenience function to get next nonce

    Args:
        address: Wallet address

    Returns:
        int: Next nonce
    """
    tracker = get_nonce_tracker()
    return tracker.get_next_nonce(address)
