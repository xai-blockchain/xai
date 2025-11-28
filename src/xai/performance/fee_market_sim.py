"""
Fee Market Simulation
Task 266: Complete fee market simulation for testing

Simulates fee market dynamics to test fee estimation and pricing.
"""

from __future__ import annotations

import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SimulatedTransaction:
    """Simulated transaction for fee market testing"""
    txid: str
    fee: float
    size: int
    priority: str  # 'low', 'medium', 'high'
    timestamp: float
    confirmed: bool = False
    confirmation_time: Optional[float] = None


class FeeMarketSimulator:
    """
    Simulate fee market dynamics

    Tests fee estimation algorithms and market behavior
    under various conditions.
    """

    def __init__(self, block_time: float = 60.0, block_size_limit: int = 1000000):
        """
        Initialize fee market simulator

        Args:
            block_time: Average time between blocks (seconds)
            block_size_limit: Maximum block size in bytes
        """
        self.block_time = block_time
        self.block_size_limit = block_size_limit

        self.pending_transactions: List[SimulatedTransaction] = []
        self.confirmed_transactions: List[SimulatedTransaction] = []
        self.current_block_number = 0
        self.simulation_time = 0.0

        # Fee statistics
        self.fee_history: List[float] = []
        self.block_utilization: List[float] = []

    def add_transaction(
        self,
        fee: float,
        size: int = 250,
        priority: str = 'medium'
    ) -> SimulatedTransaction:
        """
        Add transaction to mempool

        Args:
            fee: Transaction fee
            size: Transaction size in bytes
            priority: Transaction priority

        Returns:
            Simulated transaction
        """
        tx = SimulatedTransaction(
            txid=f"sim_tx_{len(self.pending_transactions)}_{int(time.time())}",
            fee=fee,
            size=size,
            priority=priority,
            timestamp=self.simulation_time
        )

        self.pending_transactions.append(tx)
        return tx

    def simulate_block(self) -> Dict[str, Any]:
        """
        Simulate block production

        Returns:
            Block statistics
        """
        self.current_block_number += 1
        self.simulation_time += self.block_time

        # Sort transactions by fee rate (fee per byte)
        self.pending_transactions.sort(
            key=lambda tx: tx.fee / tx.size,
            reverse=True
        )

        # Fill block with highest fee transactions
        block_transactions = []
        block_size = 0

        for tx in self.pending_transactions[:]:
            if block_size + tx.size <= self.block_size_limit:
                tx.confirmed = True
                tx.confirmation_time = self.simulation_time
                block_transactions.append(tx)
                block_size += tx.size
                self.pending_transactions.remove(tx)
                self.confirmed_transactions.append(tx)
            else:
                break

        # Record statistics
        utilization = (block_size / self.block_size_limit) * 100
        self.block_utilization.append(utilization)

        if block_transactions:
            avg_fee = sum(tx.fee for tx in block_transactions) / len(block_transactions)
            self.fee_history.append(avg_fee)

        return {
            "block_number": self.current_block_number,
            "transactions": len(block_transactions),
            "block_size": block_size,
            "utilization": utilization,
            "average_fee": avg_fee if block_transactions else 0,
            "pending_count": len(self.pending_transactions)
        }

    def simulate_congestion(self, duration_blocks: int = 10, tx_rate: int = 100) -> None:
        """
        Simulate network congestion

        Args:
            duration_blocks: Duration in blocks
            tx_rate: Transactions per block
        """
        for _ in range(duration_blocks):
            # Add many transactions
            for _ in range(tx_rate):
                fee = random.uniform(0.001, 0.1)
                priority = random.choice(['low', 'medium', 'high'])
                self.add_transaction(fee, priority=priority)

            self.simulate_block()

    def estimate_fee(self, confirmation_target: int = 3) -> float:
        """
        Estimate fee for target confirmation time

        Args:
            confirmation_target: Target blocks for confirmation

        Returns:
            Recommended fee
        """
        if not self.fee_history:
            return 0.001  # Default minimum fee

        # Use recent fee history
        recent_fees = self.fee_history[-10:]

        # For fast confirmation, use high percentile
        if confirmation_target == 1:
            return max(recent_fees) * 1.2
        elif confirmation_target <= 3:
            return sum(recent_fees) / len(recent_fees) * 1.1
        else:
            return min(recent_fees) * 1.05

    def get_mempool_stats(self) -> Dict[str, Any]:
        """Get mempool statistics"""
        if not self.pending_transactions:
            return {
                "size": 0,
                "total_fees": 0,
                "average_fee": 0,
                "min_fee": 0,
                "max_fee": 0
            }

        fees = [tx.fee for tx in self.pending_transactions]

        return {
            "size": len(self.pending_transactions),
            "total_fees": sum(fees),
            "average_fee": sum(fees) / len(fees),
            "min_fee": min(fees),
            "max_fee": max(fees)
        }

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get overall simulation statistics"""
        return {
            "blocks_simulated": self.current_block_number,
            "simulation_time": self.simulation_time,
            "total_transactions": len(self.confirmed_transactions),
            "pending_transactions": len(self.pending_transactions),
            "average_block_utilization": sum(self.block_utilization) / max(1, len(self.block_utilization)),
            "average_fee": sum(self.fee_history) / max(1, len(self.fee_history))
        }


class DynamicFeeEstimator:
    """
    Dynamic fee estimator based on market conditions

    Adjusts fee estimates based on network congestion
    """

    def __init__(self):
        self.fee_samples: List[float] = []
        self.max_samples = 100
        self.min_fee = 0.0001
        self.max_fee = 1.0

    def add_sample(self, fee: float) -> None:
        """Add fee sample from confirmed transaction"""
        self.fee_samples.append(fee)

        # Keep only recent samples
        if len(self.fee_samples) > self.max_samples:
            self.fee_samples.pop(0)

    def estimate_fee(
        self,
        priority: str = 'medium',
        size: int = 250
    ) -> float:
        """
        Estimate fee based on priority and size

        Args:
            priority: 'low', 'medium', or 'high'
            size: Transaction size in bytes

        Returns:
            Estimated fee
        """
        if not self.fee_samples:
            base_fee = self.min_fee
        else:
            # Calculate percentile based on priority
            sorted_fees = sorted(self.fee_samples)

            if priority == 'high':
                # 90th percentile
                idx = int(len(sorted_fees) * 0.9)
                base_fee = sorted_fees[idx]
            elif priority == 'medium':
                # Median
                idx = len(sorted_fees) // 2
                base_fee = sorted_fees[idx]
            else:  # low
                # 10th percentile
                idx = int(len(sorted_fees) * 0.1)
                base_fee = sorted_fees[idx]

        # Adjust for size (larger transactions pay more)
        fee = base_fee * (size / 250)  # 250 bytes is baseline

        # Apply limits
        fee = max(self.min_fee, min(fee, self.max_fee))

        return fee

    def get_fee_range(self) -> Dict[str, float]:
        """Get current fee range"""
        if not self.fee_samples:
            return {
                "min": self.min_fee,
                "max": self.min_fee,
                "average": self.min_fee
            }

        return {
            "min": min(self.fee_samples),
            "max": max(self.fee_samples),
            "average": sum(self.fee_samples) / len(self.fee_samples)
        }


class CongestionMonitor:
    """Monitor network congestion for fee estimation"""

    def __init__(self):
        self.mempool_sizes: List[int] = []
        self.block_utilizations: List[float] = []
        self.max_history = 20

    def update(self, mempool_size: int, block_utilization: float) -> None:
        """Update congestion metrics"""
        self.mempool_sizes.append(mempool_size)
        self.block_utilizations.append(block_utilization)

        # Keep limited history
        if len(self.mempool_sizes) > self.max_history:
            self.mempool_sizes.pop(0)
        if len(self.block_utilizations) > self.max_history:
            self.block_utilizations.pop(0)

    def get_congestion_level(self) -> str:
        """
        Get current congestion level

        Returns:
            'low', 'medium', or 'high'
        """
        if not self.mempool_sizes or not self.block_utilizations:
            return 'low'

        avg_mempool = sum(self.mempool_sizes) / len(self.mempool_sizes)
        avg_utilization = sum(self.block_utilizations) / len(self.block_utilizations)

        # High congestion: large mempool and high block utilization
        if avg_mempool > 1000 and avg_utilization > 90:
            return 'high'
        elif avg_mempool > 500 or avg_utilization > 70:
            return 'medium'
        else:
            return 'low'

    def get_fee_multiplier(self) -> float:
        """
        Get fee multiplier based on congestion

        Returns:
            Multiplier for base fee
        """
        level = self.get_congestion_level()

        if level == 'high':
            return 2.0
        elif level == 'medium':
            return 1.5
        else:
            return 1.0
