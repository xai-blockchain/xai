"""Adaptive fee estimation utilities for AXN nodes."""

from __future__ import annotations

from dataclasses import dataclass


PRIORITY_MULTIPLIERS = {
    "slow": 0.75,
    "normal": 1.0,
    "fast": 1.35,
    "urgent": 1.65,
}


@dataclass
class FeeRecommendation:
    fee_per_byte: float
    estimated_blocks: int
    priority: str
    pending_transactions: int


class FeeOptimizer:
    """Lightweight fee prediction model.

    Uses mempool depth and requested priority to provide a suggested
    satoshi-per-byte fee. This keeps the API functional even before a more
    advanced ML-backed optimizer is introduced.
    """

    def __init__(self, base_fee: float = 25.0) -> None:
        self.base_fee = base_fee

    def predict_optimal_fee(self, pending_tx_count: int, priority: str = "normal") -> dict:
        priority_key = priority.lower()
        multiplier = PRIORITY_MULTIPLIERS.get(priority_key, PRIORITY_MULTIPLIERS["normal"])
        mempool_factor = 1 + min(pending_tx_count, 10_000) / 10_000
        fee_per_byte = round(self.base_fee * multiplier * mempool_factor, 2)
        estimated_blocks = max(1, int(3 / multiplier))

        recommendation = FeeRecommendation(
            fee_per_byte=fee_per_byte,
            estimated_blocks=estimated_blocks,
            priority=priority_key,
            pending_transactions=pending_tx_count,
        )

        return {
            "success": True,
            "priority": recommendation.priority,
            "recommended_fee_per_byte": recommendation.fee_per_byte,
            "estimated_confirmation_blocks": recommendation.estimated_blocks,
            "pending_transactions": recommendation.pending_transactions,
        }


__all__ = ["FeeOptimizer"]
