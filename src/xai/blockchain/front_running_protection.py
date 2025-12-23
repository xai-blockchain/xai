from __future__ import annotations

import hashlib
import json
import logging
import secrets
from typing import Any

logger = logging.getLogger("xai.blockchain.front_running_protection")

class FrontRunningProtectionManager:
    def __init__(self):
        self.committed_transactions: dict[str, dict[str, Any]] = (
            {}
        )  # {commit_hash: {"sender": str, "revealed_tx": dict, "salt": str, "status": str}}
        self.revealed_transactions: dict[str, dict[str, Any]] = {}  # {tx_hash: tx_details}
        self.mempool_transactions: dict[str, dict[str, Any]] = {}  # Simulated mempool for ordering

    def _hash_transaction_with_salt(self, transaction: dict[str, Any], salt: str) -> str:
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
        logger.info("Transaction committed by %s (hash %s...)", sender_address, commit_hash[:10])
        return True

    def reveal_transaction(self, sender_address: str, transaction: dict[str, Any], salt: str):
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
        logger.info("Transaction %s... revealed by %s", tx_hash_for_processing[:10], sender_address)
        return True

    def process_mempool_with_fair_ordering(self):
        """
        Simulates processing transactions from a mempool with a conceptual fair ordering.
        In a real system, this would involve complex cryptographic sortition or VDFs.
        Here, we'll just process revealed transactions in a "fair" (e.g., random or timestamp-based) order.
        """
        logger.info("Processing mempool with fair ordering (%d transactions)", len(self.revealed_transactions))
        # For simplicity, we'll just process all revealed transactions.
        # In a real system, this would be a batch from the mempool.

        # Use cryptographically secure shuffling to ensure unpredictable transaction ordering
        # This prevents front-running attacks by making order manipulation infeasible
        ordered_tx_hashes = list(self.revealed_transactions.keys())
        sr = secrets.SystemRandom()
        sr.shuffle(ordered_tx_hashes)

        for tx_hash in ordered_tx_hashes:
            tx = self.revealed_transactions[tx_hash]
            logger.info("Processing transaction %s...: %s", tx_hash[:10], tx)
            # Here, actual execution of the transaction would occur.
            # After processing, remove from revealed_transactions
            # Also remove from committed_transactions if it exists
            for commit_hash, entry in list(self.committed_transactions.items()):
                if entry.get("revealed_tx") == tx:  # Simple check, in real system would be by hash
                    del self.committed_transactions[commit_hash]
                    break
            del self.revealed_transactions[tx_hash]
        logger.info("Mempool processing complete.")

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
            logger.warning(
                "Slippage FAILED: requested %.4f, actual %.4f, slippage %.2f%% (max %.2f%%)",
                requested_amount,
                actual_amount,
                slippage,
                max_slippage_percent,
            )
            return False
        else:
            logger.info(
                "Slippage passed: requested %.4f, actual %.4f, slippage %.2f%% (max %.2f%%)",
                requested_amount,
                actual_amount,
                slippage,
                max_slippage_percent,
            )
            return True
