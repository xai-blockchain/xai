import hashlib
import json
from typing import Dict, Any


class FrontRunningProtectionManager:
    def __init__(self):
        self.committed_transactions: Dict[str, Dict[str, Any]] = (
            {}
        )  # {commit_hash: {"sender": str, "revealed_tx": dict, "salt": str, "status": str}}
        self.revealed_transactions: Dict[str, Dict[str, Any]] = {}  # {tx_hash: tx_details}
        self.mempool_transactions: Dict[str, Dict[str, Any]] = {}  # Simulated mempool for ordering

    def _hash_transaction_with_salt(self, transaction: Dict[str, Any], salt: str) -> str:
        """Generates a consistent hash for a transaction including a salt."""
        data_to_hash = {"transaction": transaction, "salt": salt}
        return hashlib.sha256(json.dumps(data_to_hash, sort_keys=True).encode()).hexdigest()

    def commit_transaction(self, sender_address: str, commit_hash: str):
        """
        Simulates the commit phase of a commit-reveal scheme.
        Users submit a hash of their transaction (which includes a salt).
        """
        if commit_hash in self.committed_transactions:
            raise ValueError(f"Commit hash {commit_hash} already committed.")

        self.committed_transactions[commit_hash] = {
            "sender": sender_address,
            "status": "committed",
            "revealed_tx": None,  # Will be filled during reveal phase
            "salt": None,  # Will be filled during reveal phase
        }
        print(f"Transaction committed by {sender_address} with commit hash: {commit_hash[:10]}...")
        return True

    def reveal_transaction(self, sender_address: str, transaction: Dict[str, Any], salt: str):
        """
        Simulates the reveal phase of a commit-reveal scheme.
        Users reveal their full transaction and the salt, which is then checked against the committed hash.
        """
        computed_commit_hash = self._hash_transaction_with_salt(transaction, salt)
        committed_entry = self.committed_transactions.get(computed_commit_hash)

        if not committed_entry:
            raise ValueError(
                f"No matching commit found for computed hash {computed_commit_hash[:10]}..."
            )
        if committed_entry["sender"] != sender_address:
            raise PermissionError(f"Sender mismatch for commit {computed_commit_hash[:10]}...")
        if committed_entry["status"] != "committed":
            raise ValueError(f"Commit {computed_commit_hash[:10]}... is not in 'committed' status.")

        committed_entry["revealed_tx"] = transaction
        committed_entry["salt"] = salt
        committed_entry["status"] = "revealed"

        tx_hash_for_processing = self._hash_transaction_with_salt(
            transaction, salt
        )  # Use the full hash for internal tracking
        self.revealed_transactions[tx_hash_for_processing] = transaction
        print(f"Transaction {tx_hash_for_processing[:10]}... revealed by {sender_address}.")
        return True

    def process_mempool_with_fair_ordering(self):
        """
        Simulates processing transactions from a mempool with a conceptual fair ordering.
        In a real system, this would involve complex cryptographic sortition or VDFs.
        Here, we'll just process revealed transactions in a "fair" (e.g., random or timestamp-based) order.
        """
        print("\n--- Processing mempool with fair ordering ---")
        # For simplicity, we'll just process all revealed transactions.
        # In a real system, this would be a batch from the mempool.

        # Simulate a fair ordering (e.g., random for demonstration)
        ordered_tx_hashes = list(self.revealed_transactions.keys())
        import random

        random.shuffle(ordered_tx_hashes)

        for tx_hash in ordered_tx_hashes:
            tx = self.revealed_transactions[tx_hash]
            print(f"Processing transaction {tx_hash[:10]}...: {tx}")
            # Here, actual execution of the transaction would occur.
            # After processing, remove from revealed_transactions
            # Also remove from committed_transactions if it exists
            for commit_hash, entry in list(self.committed_transactions.items()):
                if entry.get("revealed_tx") == tx:  # Simple check, in real system would be by hash
                    del self.committed_transactions[commit_hash]
                    break
            del self.revealed_transactions[tx_hash]
        print("Mempool processing complete.")

    def check_slippage(
        self, requested_amount: float, actual_amount: float, max_slippage_percent: float
    ) -> bool:
        """
        Checks if the actual amount received is within the acceptable slippage tolerance.
        """
        if not isinstance(requested_amount, (int, float)) or requested_amount <= 0:
            raise ValueError("Requested amount must be a positive number.")
        if not isinstance(actual_amount, (int, float)) or actual_amount <= 0:
            raise ValueError("Actual amount must be a positive number.")
        if not isinstance(max_slippage_percent, (int, float)) or not (
            0 <= max_slippage_percent < 100
        ):
            raise ValueError("Max slippage percent must be between 0 and 100 (exclusive of 100).")

        slippage = ((requested_amount - actual_amount) / requested_amount) * 100
        if slippage > max_slippage_percent:
            print(
                f"Slippage check FAILED: Requested {requested_amount}, Actual {actual_amount}, "
                f"Slippage {slippage:.2f}%, Max allowed {max_slippage_percent:.2f}%."
            )
            return False
        else:
            print(
                f"Slippage check PASSED: Requested {requested_amount}, Actual {actual_amount}, "
                f"Slippage {slippage:.2f}%, Max allowed {max_slippage_percent:.2f}%."
            )
            return True


# Example Usage (for testing purposes)
if __name__ == "__main__":
    protection_manager = FrontRunningProtectionManager()

    user_a = "0xUserA"
    user_b = "0xUserB"

    # Simulate a transaction from User A with a salt
    tx_a_original = {
        "type": "swap",
        "token_in": "ETH",
        "amount_in": 1.0,
        "token_out": "USDC",
        "min_amount_out": 1950.0,
    }
    salt_a = "random_salt_a_123"
    commit_hash_a = protection_manager._hash_transaction_with_salt(tx_a_original, salt_a)

    # Simulate a transaction from User B with a salt
    tx_b_original = {"type": "liquidation", "target": "0xDefiLoan1", "amount": 100}
    salt_b = "another_random_salt_b_456"
    commit_hash_b = protection_manager._hash_transaction_with_salt(tx_b_original, salt_b)

    print("--- Commit Phase ---")
    protection_manager.commit_transaction(user_a, commit_hash_a)
    protection_manager.commit_transaction(user_b, commit_hash_b)

    print("\n--- Reveal Phase ---")
    protection_manager.reveal_transaction(user_a, tx_a_original, salt_a)
    protection_manager.reveal_transaction(user_b, tx_b_original, salt_b)

    protection_manager.process_mempool_with_fair_ordering()

    print("\n--- Slippage Protection Example ---")
    # User requests to swap 1 ETH for at least 1950 USDC
    requested_usdc = 1950.0

    # Scenario 1: Actual amount received is good
    actual_usdc_good = 1960.0
    protection_manager.check_slippage(requested_usdc, actual_usdc_good, max_slippage_percent=0.5)

    # Scenario 2: Actual amount received is within tolerance
    actual_usdc_ok = 1945.0  # 0.25% slippage
    protection_manager.check_slippage(requested_usdc, actual_usdc_ok, max_slippage_percent=0.5)

    # Scenario 3: Actual amount received is too low (high slippage)
    actual_usdc_bad = 1900.0  # ~2.5% slippage
    protection_manager.check_slippage(requested_usdc, actual_usdc_bad, max_slippage_percent=0.5)
