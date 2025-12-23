from __future__ import annotations

"""
Lightweight fee optimizer that returns heuristic fee recommendations.
"""

class AIFeeOptimizer:
    """Simple fee optimizer that mimics EMA-based recommendations."""

    def __init__(self):
        self.fee_history: list[float] = []

    def predict_optimal_fee(
        self, pending_tx_count: int, priority: str = "normal"
    ) -> dict[str, object]:
        base_fee = 0.05
        priority = priority.lower()

        if priority == "high":
            base_fee *= 1.5
        elif priority == "low":
            base_fee *= 0.75

        congestion = min(pending_tx_count / 100.0, 2.0)
        recommended_fee = round(base_fee * (1 + congestion), 8)

        self.fee_history.append(recommended_fee)

        return {
            "recommended_fee": recommended_fee,
            "conditions": {
                "priority": priority,
                "pending_transactions": pending_tx_count,
                "congestion_factor": round(congestion, 2),
            },
            "confidence": min(1.0, 0.5 + len(self.fee_history) * 0.05),
        }
