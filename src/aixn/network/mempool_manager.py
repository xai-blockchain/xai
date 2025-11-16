import heapq
import time
from typing import Dict, Any, Tuple


class MempoolManager:
    def __init__(self, max_transactions: int = 1000, eviction_policy: str = "fifo"):
        if not isinstance(max_transactions, int) or max_transactions <= 0:
            raise ValueError("Max transactions must be a positive integer.")
        if eviction_policy not in ["fifo", "lowest_fee"]:
            raise ValueError("Eviction policy must be 'fifo' or 'lowest_fee'.")

        self.max_transactions = max_transactions
        self.eviction_policy = eviction_policy

        # For FIFO: {tx_id: {"timestamp": int, "details": Any}}
        # For lowest_fee: min-heap of (fee, timestamp, tx_id)
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_queue: list[Tuple[float, int, str]] = []  # For lowest_fee policy
        self._transaction_id_counter = 0
        print(
            f"MempoolManager initialized. Max transactions: {self.max_transactions}, Eviction policy: {self.eviction_policy}."
        )

    def add_transaction(self, transaction_details: Any, fee: float = 0.0) -> str:
        """
        Adds a transaction to the mempool, enforcing the size limit.
        If the mempool is full, an eviction policy is applied.
        """
        self._transaction_id_counter += 1
        tx_id = f"tx_{self._transaction_id_counter}"
        current_time = int(time.time())

        if len(self.pending_transactions) >= self.max_transactions:
            print(f"Mempool is full. Applying eviction policy: {self.eviction_policy}.")
            if self.eviction_policy == "fifo":
                # Find and evict the oldest transaction
                oldest_tx_id = min(
                    self.pending_transactions,
                    key=lambda k: self.pending_transactions[k]["timestamp"],
                )
                self.remove_transaction(oldest_tx_id)
                print(f"Evicted oldest transaction: {oldest_tx_id}")
            elif self.eviction_policy == "lowest_fee":
                # Evict the transaction with the lowest fee
                if self.transaction_queue:
                    lowest_fee_tx = heapq.heappop(self.transaction_queue)
                    evicted_tx_id = lowest_fee_tx[2]
                    self.remove_transaction(evicted_tx_id)
                    print(
                        f"Evicted lowest fee transaction: {evicted_tx_id} with fee {lowest_fee_tx[0]:.2f}"
                    )
                else:
                    # Should not happen if pending_transactions is not empty
                    raise RuntimeError(
                        "Mempool full but transaction_queue is empty for lowest_fee policy."
                    )

        self.pending_transactions[tx_id] = {
            "timestamp": current_time,
            "fee": fee,
            "details": transaction_details,
        }
        if self.eviction_policy == "lowest_fee":
            heapq.heappush(
                self.transaction_queue, (fee, current_time, tx_id)
            )  # Use timestamp as tie-breaker

        print(
            f"Added transaction {tx_id} (Fee: {fee:.2f}). Mempool size: {len(self.pending_transactions)}"
        )
        return tx_id

    def remove_transaction(self, tx_id: str):
        """Removes a transaction from the mempool."""
        if tx_id in self.pending_transactions:
            del self.pending_transactions[tx_id]
            # For lowest_fee policy, removing from heap is more complex (lazy deletion or rebuild)
            # For simplicity in this conceptual model, we'll assume it's handled or not critical for removal.
            # In a real system, you'd need to mark it as removed or rebuild the heap.
            print(f"Removed transaction {tx_id}. Mempool size: {len(self.pending_transactions)}")
        else:
            print(f"Transaction {tx_id} not found in mempool.")

    def get_mempool_size(self) -> int:
        """Returns the current number of transactions in the mempool."""
        return len(self.pending_transactions)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    print("\n--- FIFO Eviction Policy ---")
    fifo_mempool = MempoolManager(max_transactions=3, eviction_policy="fifo")
    fifo_mempool.add_transaction("tx_A_details", fee=10)
    fifo_mempool.add_transaction("tx_B_details", fee=20)
    fifo_mempool.add_transaction("tx_C_details", fee=30)
    fifo_mempool.add_transaction("tx_D_details", fee=40)  # Should evict tx_A

    print("\n--- Lowest Fee Eviction Policy ---")
    lowest_fee_mempool = MempoolManager(max_transactions=3, eviction_policy="lowest_fee")
    lowest_fee_mempool.add_transaction("tx_X_details", fee=50)
    lowest_fee_mempool.add_transaction("tx_Y_details", fee=10)
    lowest_fee_mempool.add_transaction("tx_Z_details", fee=30)
    lowest_fee_mempool.add_transaction("tx_W_details", fee=5)  # Should evict tx_Y
    lowest_fee_mempool.add_transaction("tx_V_details", fee=20)  # Should evict tx_W
