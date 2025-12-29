"""Adaptive fee estimation utilities for AXN nodes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

PRIORITY_MULTIPLIERS = {
    "slow": 0.75,
    "normal": 1.0,
    "fast": 1.35,
    "urgent": 1.65,
}

PRIORITY_QUANTILES = {
    "slow": 0.35,
    "normal": 0.5,
    "fast": 0.75,
    "urgent": 0.9,
}

@dataclass
class FeeRecommendation:
    fee_per_byte: float
    estimated_blocks: int
    priority: str
    pending_transactions: int
    mempool_bytes: int = 0
    congestion_level: str = "low"
    percentiles: dict[str, float] = field(default_factory=dict)
    backlog_ratio: float = 0.0
    block_capacity: int = 0

class FeeOptimizer:
    """Derives fee guidance from mempool pressure and fee rate percentiles."""

    def __init__(self, base_fee: float = 25.0) -> None:
        self.base_fee = base_fee

    def predict_optimal_fee(
        self,
        pending_tx_count: int,
        priority: str = "normal",
        *,
        fee_rates: list[float] | None = None,
        mempool_bytes: int | None = None,
        avg_block_capacity: int = 500,
    ) -> dict[str, object]:
        priority_key = priority.lower()
        multiplier = PRIORITY_MULTIPLIERS.get(priority_key, PRIORITY_MULTIPLIERS["normal"])
        quantile = PRIORITY_QUANTILES.get(priority_key, PRIORITY_QUANTILES["normal"])

        sanitized_rates = self._sanitize_rates(fee_rates)
        percentiles = self._build_percentiles(sanitized_rates)
        if sanitized_rates:
            base_rate = self._percentile(sanitized_rates, quantile)
        else:
            base_rate = self.base_fee * multiplier

        pending = max(0, int(pending_tx_count))
        block_capacity = max(1, int(avg_block_capacity))
        backlog_ratio = pending / block_capacity
        congestion_multiplier = 1 + min(backlog_ratio, 5.0) * 0.15
        recommended_fee = round(base_rate * congestion_multiplier, 8)
        estimated_blocks = max(1, int(math.ceil(max(backlog_ratio, 0.2) * (1.0 / multiplier))))
        congestion_level = self._congestion_label(backlog_ratio)
        mempool_bytes_value = max(0, int(mempool_bytes or 0))

        recommendation = FeeRecommendation(
            fee_per_byte=recommended_fee,
            estimated_blocks=estimated_blocks,
            priority=priority_key,
            pending_transactions=pending,
            mempool_bytes=mempool_bytes_value,
            congestion_level=congestion_level,
            percentiles=percentiles,
            backlog_ratio=backlog_ratio,
            block_capacity=block_capacity,
        )

        pressure = {
            "backlog_ratio": round(recommendation.backlog_ratio, 3),
            "block_capacity": recommendation.block_capacity,
        }

        return {
            "success": True,
            "priority": recommendation.priority,
            "recommended_fee": recommendation.fee_per_byte,
            "recommended_fee_per_byte": recommendation.fee_per_byte,
            "estimated_confirmation_blocks": recommendation.estimated_blocks,
            "pending_transactions": recommendation.pending_transactions,
            "mempool_bytes": recommendation.mempool_bytes,
            "congestion_level": recommendation.congestion_level,
            "fee_percentiles": recommendation.percentiles,
            "pressure": pressure,
            "conditions": {
                "priority": recommendation.priority,
                "pending_transactions": recommendation.pending_transactions,
                "congestion_level": recommendation.congestion_level,
                "mempool_bytes": recommendation.mempool_bytes,
            },
        }

    @staticmethod
    def _sanitize_rates(fee_rates: list[float] | None) -> list[float]:
        sanitized: list[float] = []
        if not fee_rates:
            return sanitized
        for raw in fee_rates:
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if value <= 0 or not math.isfinite(value):
                continue
            sanitized.append(value)
        sanitized.sort()
        return sanitized

    def _build_percentiles(self, sorted_rates: list[float]) -> dict[str, float]:
        if not sorted_rates:
            return {}
        return {
            "p25": round(self._percentile(sorted_rates, 0.25), 8),
            "p50": round(self._percentile(sorted_rates, 0.5), 8),
            "p75": round(self._percentile(sorted_rates, 0.75), 8),
            "p90": round(self._percentile(sorted_rates, 0.9), 8),
        }

    @staticmethod
    def _percentile(sorted_values: list[float], quantile: float) -> float:
        if not sorted_values:
            return 0.0
        quantile = min(max(float(quantile), 0.0), 1.0)
        if quantile == 0.0:
            return sorted_values[0]
        if quantile == 1.0:
            return sorted_values[-1]

        position = (len(sorted_values) - 1) * quantile
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return sorted_values[int(position)]

        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        fraction = position - lower_index
        return lower_value + (upper_value - lower_value) * fraction

    @staticmethod
    def _congestion_label(backlog_ratio: float) -> str:
        if backlog_ratio < 0.5:
            return "low"
        if backlog_ratio < 1.0:
            return "moderate"
        if backlog_ratio < 2.0:
            return "high"
        return "critical"

__all__ = ["FeeOptimizer", "FeeRecommendation"]
