from typing import Dict


class NonceManager:
    def __init__(self):
        # Stores the last successfully processed nonce for each sender address
        self.last_nonces: Dict[str, int] = {}

    def get_current_nonce(self, sender_address: str) -> int:
        """
        Returns the expected next nonce for a given sender address.
        If no nonce has been seen for this address, it returns 0 (or 1, depending on convention).
        We'll use 0 as the initial state, meaning the first valid nonce should be 1.
        """
        return self.last_nonces.get(sender_address, 0)

    def check_and_increment_nonce(self, sender_address: str, incoming_nonce: int) -> bool:
        """
        Checks if the incoming nonce is valid for the sender and, if so, increments the stored nonce.
        Returns True if the nonce is valid and processed, False otherwise.
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
