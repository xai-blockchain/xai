"""
Transaction Batching for Efficiency
Task 264: Implement transaction batching for efficiency

This module provides transaction batching to improve throughput
and reduce per-transaction overhead.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TransactionBatch:
    """Batch of transactions"""
    transactions: list[Any]
    batch_id: str
    created_at: float
    size: int
    total_fees: float

    def get_average_fee(self) -> float:
        """Get average fee per transaction"""
        return self.total_fees / max(1, len(self.transactions))

class TransactionBatcher:
    """
    Batch transactions for efficient processing

    Benefits:
    - Reduced per-transaction overhead
    - Better resource utilization
    - Improved throughput
    """

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_time: float = 5.0,
        min_batch_size: int = 10
    ):
        """
        Initialize transaction batcher

        Args:
            max_batch_size: Maximum transactions per batch
            max_wait_time: Maximum time to wait before processing batch (seconds)
            min_batch_size: Minimum transactions to create a batch
        """
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.min_batch_size = min_batch_size

        self.pending_transactions: list[Any] = []
        self.batch_start_time: float | None = None
        self.processed_batches: list[TransactionBatch] = []
        self.batch_counter = 0

    def add_transaction(self, transaction: Any) -> TransactionBatch | None:
        """
        Add transaction to batch

        Args:
            transaction: Transaction to add

        Returns:
            TransactionBatch if batch is ready, None otherwise
        """
        # Initialize batch start time if first transaction
        if not self.pending_transactions:
            self.batch_start_time = time.time()

        self.pending_transactions.append(transaction)

        # Check if batch is ready
        if self._should_process_batch():
            return self._create_batch()

        return None

    def _should_process_batch(self) -> bool:
        """Check if batch should be processed"""
        # Batch is full
        if len(self.pending_transactions) >= self.max_batch_size:
            return True

        # Batch has waited long enough and meets minimum size
        if self.batch_start_time:
            elapsed = time.time() - self.batch_start_time
            if elapsed >= self.max_wait_time and len(self.pending_transactions) >= self.min_batch_size:
                return True

        return False

    def _create_batch(self) -> TransactionBatch:
        """Create batch from pending transactions"""
        self.batch_counter += 1

        # Calculate total fees
        total_fees = sum(
            getattr(tx, 'fee', 0) for tx in self.pending_transactions
        )

        batch = TransactionBatch(
            transactions=self.pending_transactions.copy(),
            batch_id=f"batch_{self.batch_counter}_{int(time.time())}",
            created_at=time.time(),
            size=len(self.pending_transactions),
            total_fees=total_fees
        )

        self.processed_batches.append(batch)

        # Clear pending
        self.pending_transactions.clear()
        self.batch_start_time = None

        return batch

    def force_batch(self) -> TransactionBatch | None:
        """Force creation of batch regardless of size"""
        if not self.pending_transactions:
            return None

        return self._create_batch()

    def get_pending_count(self) -> int:
        """Get number of pending transactions"""
        return len(self.pending_transactions)

    def get_batch_stats(self) -> dict[str, Any]:
        """Get batching statistics"""
        if not self.processed_batches:
            return {
                "total_batches": 0,
                "total_transactions": 0,
                "average_batch_size": 0,
                "pending_transactions": len(self.pending_transactions)
            }

        total_txs = sum(b.size for b in self.processed_batches)
        avg_size = total_txs / len(self.processed_batches)

        return {
            "total_batches": len(self.processed_batches),
            "total_transactions": total_txs,
            "average_batch_size": avg_size,
            "pending_transactions": len(self.pending_transactions),
            "max_batch_size": self.max_batch_size,
            "min_batch_size": self.min_batch_size
        }

class PriorityBatcher:
    """
    Batch transactions with priority sorting

    Higher priority transactions are processed first
    """

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_time: float = 5.0
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

        # Priority queues (high, medium, low)
        self.queues: dict[str, list[Any]] = {
            'high': [],
            'medium': [],
            'low': []
        }

        self.batch_start_time: float | None = None
        self.processed_batches: list[TransactionBatch] = []
        self.batch_counter = 0

    def add_transaction(self, transaction: Any, priority: str = 'medium') -> TransactionBatch | None:
        """
        Add transaction with priority

        Args:
            transaction: Transaction to add
            priority: 'high', 'medium', or 'low'

        Returns:
            TransactionBatch if ready
        """
        if priority not in self.queues:
            priority = 'medium'

        if not any(self.queues.values()):
            self.batch_start_time = time.time()

        self.queues[priority].append(transaction)

        if self._should_process_batch():
            return self._create_batch()

        return None

    def _should_process_batch(self) -> bool:
        """Check if should process batch"""
        total_pending = sum(len(q) for q in self.queues.values())

        if total_pending >= self.max_batch_size:
            return True

        if self.batch_start_time:
            elapsed = time.time() - self.batch_start_time
            if elapsed >= self.max_wait_time and total_pending > 0:
                return True

        return False

    def _create_batch(self) -> TransactionBatch:
        """Create batch prioritizing high-priority transactions"""
        batch_txs = []

        # Fill batch with high priority first
        for priority in ['high', 'medium', 'low']:
            queue = self.queues[priority]
            while queue and len(batch_txs) < self.max_batch_size:
                batch_txs.append(queue.pop(0))

        self.batch_counter += 1

        total_fees = sum(getattr(tx, 'fee', 0) for tx in batch_txs)

        batch = TransactionBatch(
            transactions=batch_txs,
            batch_id=f"priority_batch_{self.batch_counter}_{int(time.time())}",
            created_at=time.time(),
            size=len(batch_txs),
            total_fees=total_fees
        )

        self.processed_batches.append(batch)
        self.batch_start_time = None

        return batch

    def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics"""
        return {
            priority: len(queue)
            for priority, queue in self.queues.items()
        }

class AdaptiveBatcher:
    """
    Adaptive batcher that adjusts batch size based on load

    Increases batch size during high load, decreases during low load
    """

    def __init__(self):
        self.min_batch_size = 10
        self.max_batch_size = 500
        self.current_batch_size = 100
        self.max_wait_time = 5.0

        self.pending_transactions: list[Any] = []
        self.batch_start_time: float | None = None
        self.processed_batches: list[TransactionBatch] = []
        self.batch_counter = 0

        # Performance tracking
        self.recent_tx_rate: list[float] = []  # Transactions per second
        self.adjustment_interval = 60.0  # Adjust every 60 seconds
        self.last_adjustment = time.time()

    def add_transaction(self, transaction: Any) -> TransactionBatch | None:
        """Add transaction and adapt batch size"""
        if not self.pending_transactions:
            self.batch_start_time = time.time()

        self.pending_transactions.append(transaction)

        # Adapt batch size periodically
        self._adapt_batch_size()

        if self._should_process_batch():
            return self._create_batch()

        return None

    def _adapt_batch_size(self) -> None:
        """Adapt batch size based on transaction rate"""
        now = time.time()

        if now - self.last_adjustment < self.adjustment_interval:
            return

        # Calculate recent transaction rate
        if self.processed_batches:
            recent_batches = [
                b for b in self.processed_batches
                if now - b.created_at < self.adjustment_interval
            ]

            if recent_batches:
                total_txs = sum(b.size for b in recent_batches)
                tx_rate = total_txs / self.adjustment_interval

                # Increase batch size if high transaction rate
                if tx_rate > 100:  # More than 100 tx/s
                    self.current_batch_size = min(
                        self.current_batch_size * 1.5,
                        self.max_batch_size
                    )
                # Decrease batch size if low transaction rate
                elif tx_rate < 10:  # Less than 10 tx/s
                    self.current_batch_size = max(
                        self.current_batch_size * 0.7,
                        self.min_batch_size
                    )

        self.last_adjustment = now

    def _should_process_batch(self) -> bool:
        """Check if should process batch"""
        if len(self.pending_transactions) >= self.current_batch_size:
            return True

        if self.batch_start_time:
            elapsed = time.time() - self.batch_start_time
            if elapsed >= self.max_wait_time and len(self.pending_transactions) >= self.min_batch_size:
                return True

        return False

    def _create_batch(self) -> TransactionBatch:
        """Create batch"""
        self.batch_counter += 1

        total_fees = sum(getattr(tx, 'fee', 0) for tx in self.pending_transactions)

        batch = TransactionBatch(
            transactions=self.pending_transactions.copy(),
            batch_id=f"adaptive_batch_{self.batch_counter}_{int(time.time())}",
            created_at=time.time(),
            size=len(self.pending_transactions),
            total_fees=total_fees
        )

        self.processed_batches.append(batch)
        self.pending_transactions.clear()
        self.batch_start_time = None

        return batch

    def get_adaptive_stats(self) -> dict[str, Any]:
        """Get adaptive batching statistics"""
        return {
            "current_batch_size": self.current_batch_size,
            "min_batch_size": self.min_batch_size,
            "max_batch_size": self.max_batch_size,
            "pending_transactions": len(self.pending_transactions),
            "total_batches": len(self.processed_batches)
        }

class BatchProcessor:
    """Process transaction batches"""

    def __init__(self, process_callback: Callable[[list[Any]], bool]):
        """
        Initialize batch processor

        Args:
            process_callback: Function to process batch of transactions
        """
        self.process_callback = process_callback
        self.processed_count = 0
        self.failed_count = 0

    def process_batch(self, batch: TransactionBatch) -> bool:
        """
        Process a batch of transactions

        Args:
            batch: Transaction batch

        Returns:
            True if successful
        """
        try:
            success = self.process_callback(batch.transactions)

            if success:
                self.processed_count += len(batch.transactions)
            else:
                self.failed_count += len(batch.transactions)

            return success
        except Exception as e:
            logger.warning(
                "Exception in process_batch",
                extra={
                    "error_type": "Exception",
                    "error": str(e),
                    "function": "process_batch"
                }
            )
            self.failed_count += len(batch.transactions)
            print(f"Batch processing error: {e}")
            return False

    def get_stats(self) -> dict[str, int]:
        """Get processing statistics"""
        return {
            "processed": self.processed_count,
            "failed": self.failed_count,
            "total": self.processed_count + self.failed_count
        }
