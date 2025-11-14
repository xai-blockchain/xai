import time
from collections import deque
from typing import Deque, Tuple

class FeeAdjuster:
    def __init__(self, base_fee: float = 0.001, max_fee: float = 0.1, 
                 congestion_factor: float = 0.01, history_window_blocks: int = 10):
        if not isinstance(base_fee, (int, float)) or base_fee <= 0:
            raise ValueError("Base fee must be a positive number.")
        if not isinstance(max_fee, (int, float)) or max_fee <= base_fee:
            raise ValueError("Max fee must be greater than base fee.")
        if not isinstance(congestion_factor, (int, float)) or congestion_factor <= 0:
            raise ValueError("Congestion factor must be a positive number.")
        if not isinstance(history_window_blocks, int) or history_window_blocks <= 0:
            raise ValueError("History window blocks must be a positive integer.")

        self.base_fee = base_fee
        self.max_fee = max_fee
        self.congestion_factor = congestion_factor
        self.history_window_blocks = history_window_blocks

        # Stores historical network metrics: deque of (pending_tx_count, block_fullness)
        self.network_metrics_history: Deque[Tuple[int, float]] = deque()
        
        # Initialize with some default metrics
        self.update_network_metrics(0, 0.0)
        print(f"FeeAdjuster initialized. Base fee: {self.base_fee}, Max fee: {self.max_fee}")

    def update_network_metrics(self, pending_transactions: int, block_fullness: float):
        """
        Updates the historical network metrics.
        - pending_transactions: Number of transactions in the mempool.
        - block_fullness: A float between 0.0 and 1.0 indicating how full the last block was.
        """
        if not isinstance(pending_transactions, int) or pending_transactions < 0:
            raise ValueError("Pending transactions must be a non-negative integer.")
        if not isinstance(block_fullness, (int, float)) or not (0.0 <= block_fullness <= 1.0):
            raise ValueError("Block fullness must be between 0.0 and 1.0.")

        self.network_metrics_history.append((pending_transactions, block_fullness))
        if len(self.network_metrics_history) > self.history_window_blocks:
            self.network_metrics_history.popleft()
        print(f"Network metrics updated: Pending TXs={pending_transactions}, Block Fullness={block_fullness:.2f}")

    def get_suggested_fee(self) -> float:
        """
        Calculates a suggested transaction fee based on current and historical network congestion.
        This is a simplified model.
        """
        if not self.network_metrics_history:
            return self.base_fee

        # Average recent pending transactions and block fullness
        avg_pending_tx = sum([m[0] for m in self.network_metrics_history]) / len(self.network_metrics_history)
        avg_block_fullness = sum([m[1] for m in self.network_metrics_history]) / len(self.network_metrics_history)

        # Simple linear adjustment based on congestion
        # More sophisticated algorithms would use exponential moving averages, PID controllers, etc.
        congestion_score = (avg_pending_tx / 1000.0) + avg_block_fullness # Normalize pending_tx for example
        
        adjusted_fee = self.base_fee + (congestion_score * self.congestion_factor)
        
        # Ensure fee stays within bounds
        suggested_fee = max(self.base_fee, min(adjusted_fee, self.max_fee))
        
        print(f"Suggested fee: {suggested_fee:.4f} (Avg Pending TXs: {avg_pending_tx:.0f}, Avg Block Fullness: {avg_block_fullness:.2f})")
        return suggested_fee

# Example Usage (for testing purposes)
if __name__ == "__main__":
    fee_adjuster = FeeAdjuster(base_fee=0.001, max_fee=0.05, congestion_factor=0.005, history_window_blocks=5)

    print("\n--- Low Congestion ---")
    fee_adjuster.update_network_metrics(10, 0.1)
    fee_adjuster.update_network_metrics(15, 0.2)
    print(f"Current suggested fee: {fee_adjuster.get_suggested_fee():.4f}")

    print("\n--- Moderate Congestion ---")
    fee_adjuster.update_network_metrics(500, 0.5)
    fee_adjuster.update_network_metrics(700, 0.7)
    print(f"Current suggested fee: {fee_adjuster.get_suggested_fee():.4f}")

    print("\n--- High Congestion ---")
    fee_adjuster.update_network_metrics(1500, 0.9)
    fee_adjuster.update_network_metrics(2000, 1.0)
    fee_adjuster.update_network_metrics(2500, 1.0)
    print(f"Current suggested fee: {fee_adjuster.get_suggested_fee():.4f}")

    print("\n--- Congestion Easing ---")
    fee_adjuster.update_network_metrics(100, 0.3)
    fee_adjuster.update_network_metrics(50, 0.1)
    print(f"Current suggested fee: {fee_adjuster.get_suggested_fee():.4f}")
