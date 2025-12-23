from __future__ import annotations

import heapq
from typing import Any

# Assuming FeeAdjuster is available from a previous implementation
from src.xai.network.fee_adjuster import FeeAdjuster


class PriorityFeeManager:
    def __init__(self, fee_adjuster: FeeAdjuster, min_priority_fee: float = 0.0001):
        if not isinstance(fee_adjuster, FeeAdjuster):
            raise ValueError("fee_adjuster must be an instance of FeeAdjuster.")
        if not isinstance(min_priority_fee, (int, float)) or min_priority_fee < 0:
            raise ValueError("Minimum priority fee must be a non-negative number.")

        self.fee_adjuster = fee_adjuster
        self.min_priority_fee = min_priority_fee

        # Priority queue for transactions: min-heap of (total_fee, tx_id, transaction_details)
        self.transaction_priority_queue: list[tuple[float, str, Any]] = []
        self._transaction_id_counter = 0
        print(f"PriorityFeeManager initialized. Minimum priority fee: {self.min_priority_fee:.4f}.")

    def calculate_total_fee(self, priority_fee: float) -> float:
        """
        Calculates the total fee for a transaction, combining base fee and priority fee.
        """
        if not isinstance(priority_fee, (int, float)) or priority_fee < self.min_priority_fee:
            raise ValueError(
                f"Priority fee ({priority_fee:.4f}) must be at least the minimum ({self.min_priority_fee:.4f})."
            )

        base_fee = self.fee_adjuster.get_suggested_fee()
        total_fee = base_fee + priority_fee
        print(
            f"Base Fee: {base_fee:.4f}, Priority Fee: {priority_fee:.4f}, Total Fee: {total_fee:.4f}"
        )
        return total_fee

    def get_recommended_priority_fee(self, desired_speed: str = "medium") -> float:
        """
        Provides a conceptual recommended priority fee based on desired speed.
        In a real system, this would involve analyzing recent block inclusions.
        """
        if desired_speed == "fast":
            return self.min_priority_fee * 5  # Higher tip for faster inclusion
        elif desired_speed == "medium":
            return self.min_priority_fee * 2
        elif desired_speed == "slow":
            return self.min_priority_fee
        else:
            raise ValueError("Desired speed must be 'fast', 'medium', or 'slow'.")

    def add_transaction_to_queue(self, transaction_details: Any, priority_fee: float):
        """
        Adds a transaction to the processing queue, prioritized by total fee.
        """
        total_fee = self.calculate_total_fee(priority_fee)
        self._transaction_id_counter += 1
        tx_id = f"queued_tx_{self._transaction_id_counter}"

        # Use negative total_fee for max-heap behavior (highest fee first)
        heapq.heappush(self.transaction_priority_queue, (-total_fee, tx_id, transaction_details))
        print(f"Transaction {tx_id} added to queue with Total Fee: {total_fee:.4f}.")

    def process_next_transaction(self) -> tuple[str, Any, float] | None:
        """
        Simulates processing the next highest-priority transaction.
        Returns (tx_id, transaction_details, total_fee) or None if queue is empty.
        """
        if not self.transaction_priority_queue:
            print("Transaction queue is empty.")
            return None

        # Pop the transaction with the highest total fee
        neg_total_fee, tx_id, details = heapq.heappop(self.transaction_priority_queue)
        total_fee = -neg_total_fee
        print(f"Processing transaction {tx_id} with Total Fee: {total_fee:.4f}.")
        return tx_id, details, total_fee

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Initialize FeeAdjuster (dependency)
    fee_adjuster = FeeAdjuster(
        base_fee=0.001, max_fee=0.05, congestion_factor=0.005, history_window_blocks=5
    )
    fee_adjuster.update_network_metrics(100, 0.5)  # Simulate some network state

    manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

    print("\n--- Adding Transactions with Different Priority Fees ---")
    manager.add_transaction_to_queue("tx_A_details", manager.get_recommended_priority_fee("slow"))
    manager.add_transaction_to_queue("tx_B_details", manager.get_recommended_priority_fee("medium"))
    manager.add_transaction_to_queue("tx_C_details", manager.get_recommended_priority_fee("fast"))
    manager.add_transaction_to_queue("tx_D_details", 0.0005)  # Custom priority fee

    print("\n--- Processing Transactions (Highest Priority First) ---")
    while True:
        next_tx = manager.process_next_transaction()
        if next_tx is None:
            break
        # In a real system, this transaction would now be included in a block.
