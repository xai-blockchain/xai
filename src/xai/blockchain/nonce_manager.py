"""
Nonce Manager Module

Manages transaction nonces to prevent replay attacks and ensure proper
transaction ordering in the blockchain.

Each sender address has an incrementing nonce that must be used sequentially
to prevent duplicate transaction processing and replay attacks.
"""

import logging
from typing import Dict

logger = logging.getLogger("xai.blockchain.nonce_manager")


class NonceManager:
    """
    Manages nonces for blockchain transactions.

    Maintains the last processed nonce for each sender address and validates
    incoming transaction nonces to prevent replay attacks and ensure proper
    transaction sequencing.

    Attributes:
        last_nonces: Dictionary mapping sender addresses to their last processed nonce
    """

    def __init__(self) -> None:
        """Initialize the NonceManager with an empty nonce tracking dictionary."""
        # Stores the last successfully processed nonce for each sender address
        self.last_nonces: Dict[str, int] = {}

    def get_current_nonce(self, sender_address: str) -> int:
        """
        Get the current nonce for a sender address.

        Args:
            sender_address: The blockchain address of the sender

        Returns:
            The last processed nonce for the address, or 0 if no transactions
            have been processed yet. The first valid nonce should be 1.
        """
        return self.last_nonces.get(sender_address, 0)

    def check_and_increment_nonce(self, sender_address: str, incoming_nonce: int) -> bool:
        """
        Validate and process an incoming transaction nonce.

        Args:
            sender_address: The blockchain address of the sender
            incoming_nonce: The nonce from the incoming transaction

        Returns:
            True if the nonce is valid and has been processed, False otherwise

        Note:
            - Nonces must be sequential (expected_nonce + 1)
            - Lower nonces are rejected as potential replay attacks
            - Higher nonces are rejected to prevent out-of-order execution
        """
        expected_nonce = self.get_current_nonce(sender_address) + 1

        if incoming_nonce == expected_nonce:
            self.last_nonces[sender_address] = incoming_nonce
            logger.debug("Nonce for %s updated to %s (approved)", sender_address, incoming_nonce)
            return True
        elif incoming_nonce > expected_nonce:
            logger.warning(
                "Nonce too high for %s (incoming %s, expected %s). Rejecting.",
                sender_address,
                incoming_nonce,
                expected_nonce,
            )
            # In a real system, this might be put into a pending queue.
            return False
        else:  # incoming_nonce < expected_nonce
            logger.warning(
                "Nonce too low for %s (incoming %s, expected %s). Possible replay.",
                sender_address,
                incoming_nonce,
                expected_nonce,
            )
            return False


