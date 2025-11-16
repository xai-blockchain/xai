"""
Nonce Manager Module

Manages transaction nonces to prevent replay attacks and ensure proper
transaction ordering in the blockchain.

Each sender address has an incrementing nonce that must be used sequentially
to prevent duplicate transaction processing and replay attacks.
"""

from typing import Dict


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
            print(f"Nonce for {sender_address} updated to {incoming_nonce}. Transaction approved.")
            return True
        elif incoming_nonce > expected_nonce:
            print(
                f"Nonce for {sender_address} is too high (incoming: {incoming_nonce}, expected: {expected_nonce}). "
                f"Possible out-of-order or skipped transaction. Rejecting for now."
            )
            # In a real system, this might be put into a pending queue.
            return False
        else:  # incoming_nonce < expected_nonce
            print(
                f"Nonce for {sender_address} is too low (incoming: {incoming_nonce}, expected: {expected_nonce}). "
                f"Possible replay attack. Rejecting."
            )
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    nonce_manager = NonceManager()

    user_a = "0xUserA"
    user_b = "0xUserB"

    print("--- User A Transactions ---")
    print(f"User A current nonce: {nonce_manager.get_current_nonce(user_a)}")
    nonce_manager.check_and_increment_nonce(user_a, 1)  # Valid
    nonce_manager.check_and_increment_nonce(user_a, 2)  # Valid
    nonce_manager.check_and_increment_nonce(user_a, 2)  # Replay attack (rejected)
    nonce_manager.check_and_increment_nonce(user_a, 4)  # Too high (rejected)
    nonce_manager.check_and_increment_nonce(user_a, 3)  # Valid
    print(f"User A final nonce: {nonce_manager.get_current_nonce(user_a)}")

    print("\n--- User B Transactions ---")
    print(f"User B current nonce: {nonce_manager.get_current_nonce(user_b)}")
    nonce_manager.check_and_increment_nonce(user_b, 1)  # Valid
    nonce_manager.check_and_increment_nonce(user_b, 0)  # Too low (rejected)
    nonce_manager.check_and_increment_nonce(user_b, 2)  # Valid
    print(f"User B final nonce: {nonce_manager.get_current_nonce(user_b)}")
