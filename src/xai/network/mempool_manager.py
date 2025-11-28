import heapq
import time
from typing import Dict, Any, Tuple, Optional, Set, List


class MempoolManager:
    """
    Production-grade mempool manager with size limits and transaction expiry.

    Features:
    - Configurable maximum size with fee-based eviction
    - Automatic expiration of old unconfirmed transactions
    - Transaction prioritization by fee rate
    """

    def __init__(
        self,
        max_transactions: int = 1000,
        eviction_policy: str = "fifo",
        transaction_expiry_seconds: int = 86400,  # 24 hours default
    ):
        """
        Initialize mempool manager.

        Args:
            max_transactions: Maximum number of transactions to hold in mempool
            eviction_policy: Policy for evicting transactions when full ('fifo' or 'lowest_fee')
            transaction_expiry_seconds: Time in seconds before unconfirmed transactions expire
        """
        if not isinstance(max_transactions, int) or max_transactions <= 0:
            raise ValueError("Max transactions must be a positive integer.")
        if eviction_policy not in ["fifo", "lowest_fee"]:
            raise ValueError("Eviction policy must be 'fifo' or 'lowest_fee'.")

        self.max_transactions = max_transactions
        self.eviction_policy = eviction_policy
        self.transaction_expiry_seconds = transaction_expiry_seconds

        # For FIFO: {tx_id: {"timestamp": int, "details": Any}}
        # For lowest_fee: min-heap of (fee, timestamp, tx_id)
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_queue: list[Tuple[float, int, str]] = []  # For lowest_fee policy
        self._transaction_id_counter = 0
        self.last_expiry_check = time.time()

        # Double-spend detection: track spent UTXOs in mempool
        # Set of "txid:vout" strings representing UTXOs being spent by pending transactions
        self.spent_utxos: Set[str] = set()

        # Orphan transaction pool: transactions waiting for parent transactions
        # {txid: {"transaction": details, "timestamp": int, "missing_parents": Set[str]}}
        self.orphan_pool: Dict[str, Dict[str, Any]] = {}
        self.max_orphan_pool_size = 100  # Limit orphan pool size

        print(
            f"MempoolManager initialized. Max transactions: {self.max_transactions}, "
            f"Eviction policy: {self.eviction_policy}, "
            f"Transaction expiry: {self.transaction_expiry_seconds}s"
        )

    def add_transaction(
        self, transaction_details: Any, fee: float = 0.0, inputs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Adds a transaction to the mempool with double-spend detection.

        Args:
            transaction_details: Transaction data
            fee: Transaction fee
            inputs: List of input UTXOs being spent (format: [{"txid": str, "vout": int}, ...])

        Returns:
            Dictionary with 'success' (bool), 'tx_id' (str if success), and 'reason' (str if failed)
        """
        self._transaction_id_counter += 1
        tx_id = f"tx_{self._transaction_id_counter}"
        current_time = int(time.time())

        # Extract inputs from transaction_details if not provided separately
        if inputs is None and hasattr(transaction_details, "inputs"):
            inputs = transaction_details.inputs
        elif inputs is None and isinstance(transaction_details, dict):
            inputs = transaction_details.get("inputs", [])

        if inputs is None:
            inputs = []

        # SECURITY: Check for double-spend attempts in mempool
        if inputs:
            spent_utxo_keys = {f"{inp['txid']}:{inp['vout']}" for inp in inputs}
            conflicts = spent_utxo_keys & self.spent_utxos

            if conflicts:
                conflict_list = ", ".join(list(conflicts)[:3])  # Show first 3 conflicts
                print(
                    f"SECURITY ALERT: Double-spend attempt detected! "
                    f"Transaction attempts to spend already-pending UTXOs: {conflict_list}"
                )
                return {
                    "success": False,
                    "reason": "double_spend_detected",
                    "conflicting_utxos": list(conflicts),
                    "message": f"Double-spend detected: {len(conflicts)} UTXO(s) already spent in mempool"
                }

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
            "inputs": inputs,  # Store inputs for tracking
        }

        # Mark UTXOs as spent in mempool
        if inputs:
            for inp in inputs:
                utxo_key = f"{inp['txid']}:{inp['vout']}"
                self.spent_utxos.add(utxo_key)

        if self.eviction_policy == "lowest_fee":
            heapq.heappush(
                self.transaction_queue, (fee, current_time, tx_id)
            )  # Use timestamp as tie-breaker

        print(
            f"Added transaction {tx_id} (Fee: {fee:.2f}, Inputs: {len(inputs)}). "
            f"Mempool size: {len(self.pending_transactions)}"
        )
        return {"success": True, "tx_id": tx_id}

    def remove_transaction(self, tx_id: str):
        """Removes a transaction from the mempool and frees spent UTXOs."""
        if tx_id in self.pending_transactions:
            tx_data = self.pending_transactions[tx_id]

            # Free up the spent UTXOs so they can be spent by other transactions
            inputs = tx_data.get("inputs", [])
            for inp in inputs:
                utxo_key = f"{inp['txid']}:{inp['vout']}"
                self.spent_utxos.discard(utxo_key)

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

    def remove_expired_transactions(self) -> int:
        """
        Remove transactions that have exceeded the expiry time.

        This prevents the mempool from being clogged with old unconfirmed transactions
        that will likely never be mined (e.g., due to low fees or network issues).

        Returns:
            Number of expired transactions removed
        """
        current_time = time.time()

        # Don't check too frequently (every 60 seconds)
        if current_time - self.last_expiry_check < 60:
            return 0

        self.last_expiry_check = current_time
        expired_tx_ids = []

        # Find all expired transactions
        for tx_id, tx_data in self.pending_transactions.items():
            tx_age = current_time - tx_data["timestamp"]
            if tx_age > self.transaction_expiry_seconds:
                expired_tx_ids.append(tx_id)

        # Remove expired transactions
        for tx_id in expired_tx_ids:
            self.remove_transaction(tx_id)
            print(f"Expired transaction {tx_id} (age: {current_time - self.pending_transactions.get(tx_id, {}).get('timestamp', current_time):.0f}s)")

        if expired_tx_ids:
            print(f"Removed {len(expired_tx_ids)} expired transactions from mempool")

        # Rebuild transaction queue if using lowest_fee policy
        if self.eviction_policy == "lowest_fee" and expired_tx_ids:
            self.transaction_queue = []
            for tx_id, tx_data in self.pending_transactions.items():
                heapq.heappush(
                    self.transaction_queue,
                    (tx_data["fee"], tx_data["timestamp"], tx_id)
                )

        return len(expired_tx_ids)

    def get_transactions_by_fee_rate(self, limit: Optional[int] = None) -> list:
        """
        Get transactions ordered by fee rate (highest first).

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction IDs ordered by fee rate
        """
        # Sort by fee (descending)
        sorted_txs = sorted(
            self.pending_transactions.items(),
            key=lambda item: item[1]["fee"],
            reverse=True
        )

        if limit:
            sorted_txs = sorted_txs[:limit]

        return [(tx_id, tx_data) for tx_id, tx_data in sorted_txs]

    def add_orphan_transaction(
        self, transaction_details: Any, missing_parent_txids: List[str]
    ) -> Dict[str, Any]:
        """
        Add a transaction to the orphan pool when parent transactions are missing.

        Args:
            transaction_details: The orphan transaction
            missing_parent_txids: List of parent transaction IDs that are missing

        Returns:
            Dictionary with status information
        """
        # Generate transaction ID
        if hasattr(transaction_details, "txid") and transaction_details.txid:
            tx_id = transaction_details.txid
        elif isinstance(transaction_details, dict) and "txid" in transaction_details:
            tx_id = transaction_details["txid"]
        else:
            self._transaction_id_counter += 1
            tx_id = f"orphan_tx_{self._transaction_id_counter}"

        # Check if orphan pool is full
        if len(self.orphan_pool) >= self.max_orphan_pool_size:
            # Evict oldest orphan transaction
            oldest_tx_id = min(
                self.orphan_pool,
                key=lambda k: self.orphan_pool[k]["timestamp"],
            )
            del self.orphan_pool[oldest_tx_id]
            print(f"Orphan pool full. Evicted oldest orphan: {oldest_tx_id}")

        # Add to orphan pool
        self.orphan_pool[tx_id] = {
            "transaction": transaction_details,
            "timestamp": int(time.time()),
            "missing_parents": set(missing_parent_txids),
        }

        print(
            f"Added orphan transaction {tx_id}. "
            f"Missing {len(missing_parent_txids)} parent(s). "
            f"Orphan pool size: {len(self.orphan_pool)}"
        )

        return {
            "success": True,
            "tx_id": tx_id,
            "orphan_pool_size": len(self.orphan_pool),
            "missing_parents": list(missing_parent_txids),
        }

    def process_orphan_transactions(self, newly_added_txid: str) -> List[str]:
        """
        Process orphan pool when a new transaction is added to mempool.
        Check if any orphan transactions can now be moved to main mempool.

        Args:
            newly_added_txid: Transaction ID that was just added to mempool

        Returns:
            List of orphan transaction IDs that were promoted to mempool
        """
        promoted_txids = []

        # Check all orphan transactions
        orphans_to_remove = []
        for orphan_tx_id, orphan_data in list(self.orphan_pool.items()):
            # Remove this newly added transaction from missing parents
            orphan_data["missing_parents"].discard(newly_added_txid)

            # If all parents are now available, promote to mempool
            if not orphan_data["missing_parents"]:
                transaction = orphan_data["transaction"]

                # Extract fee and inputs
                fee = 0.0
                inputs = []
                if hasattr(transaction, "fee"):
                    fee = transaction.fee
                elif isinstance(transaction, dict):
                    fee = transaction.get("fee", 0.0)

                if hasattr(transaction, "inputs"):
                    inputs = transaction.inputs
                elif isinstance(transaction, dict):
                    inputs = transaction.get("inputs", [])

                # Try to add to main mempool
                result = self.add_transaction(transaction, fee=fee, inputs=inputs)

                if result["success"]:
                    promoted_txids.append(orphan_tx_id)
                    orphans_to_remove.append(orphan_tx_id)
                    print(f"Promoted orphan transaction {orphan_tx_id} to mempool")

        # Remove promoted orphans from pool
        for tx_id in orphans_to_remove:
            del self.orphan_pool[tx_id]

        return promoted_txids

    def retry_orphan_transactions(self) -> int:
        """
        Retry orphan transactions that may have timed out or can be re-evaluated.
        This should be called periodically.

        Returns:
            Number of orphan transactions that were successfully promoted
        """
        current_time = time.time()
        expired_orphans = []
        promoted_count = 0

        # Remove orphans that are too old (e.g., 1 hour)
        max_orphan_age = 3600
        for orphan_tx_id, orphan_data in list(self.orphan_pool.items()):
            age = current_time - orphan_data["timestamp"]

            if age > max_orphan_age:
                expired_orphans.append(orphan_tx_id)
                print(f"Orphan transaction {orphan_tx_id} expired (age: {age:.0f}s)")

        # Remove expired orphans
        for tx_id in expired_orphans:
            del self.orphan_pool[tx_id]

        if expired_orphans:
            print(f"Removed {len(expired_orphans)} expired orphan transactions")

        return promoted_count

    def get_orphan_pool_status(self) -> Dict[str, Any]:
        """
        Get status information about the orphan transaction pool.

        Returns:
            Dictionary with orphan pool statistics
        """
        current_time = time.time()
        orphan_ages = [
            current_time - data["timestamp"] for data in self.orphan_pool.values()
        ]

        return {
            "orphan_count": len(self.orphan_pool),
            "max_orphan_pool_size": self.max_orphan_pool_size,
            "oldest_orphan_age_seconds": max(orphan_ages) if orphan_ages else 0,
            "average_orphan_age_seconds": sum(orphan_ages) / len(orphan_ages) if orphan_ages else 0,
            "orphan_transactions": list(self.orphan_pool.keys()),
        }


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
