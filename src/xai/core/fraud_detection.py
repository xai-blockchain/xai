"""Heuristic fraud detection for wallet/API submissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


SUSPICIOUS_COUNTRIES = {"KP", "IR", "SY"}
HIGH_RISK_TX_TYPES = {"anonymous_bridge", "obfuscated_transfer"}


@dataclass
class FraudSignal:
    reason: str
    weight: float


class FraudDetector:
    """Rule-based fraud analysis engine."""

    def __init__(self) -> None:
        self.base_threshold = 0.6

    def analyze_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        score = 0.0
        signals: List[FraudSignal] = []

        amount = float(data.get("amount", 0))
        if amount >= 10_000:
            score += 0.35
            signals.append(FraudSignal("high_value", 0.35))

        if data.get("geolocation") in SUSPICIOUS_COUNTRIES:
            score += 0.4
            signals.append(FraudSignal("sanctioned_region", 0.4))

        tx_type = data.get("tx_type")
        if tx_type in HIGH_RISK_TX_TYPES:
            score += 0.25
            signals.append(FraudSignal("high_risk_type", 0.25))

        if data.get("address") == data.get("recipient"):
            score += 0.1
            signals.append(FraudSignal("self_transfer", 0.1))

        justification = [f"{sig.reason}:{sig.weight:.2f}" for sig in signals]
        return {
            "success": True,
            "score": round(score, 3),
            "threshold": self.base_threshold,
            "flags": justification,
            "action": "review" if score >= self.base_threshold else "allow",
        }


__all__ = ["FraudDetector"]
