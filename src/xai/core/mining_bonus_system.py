"""Adapter around the mining bonus manager for node orchestration."""

from __future__ import annotations

from typing import Dict, Any

from xai.core.mining_bonuses import MiningBonusManager


class MiningBonusSystem:
    """Facade used by API routes to access bonus data."""

    def __init__(self) -> None:
        self.manager = MiningBonusManager()

    def register_miner(self, address: str) -> Dict[str, Any]:
        return self.manager.register_miner(address)

    def get_bonus_stats(self) -> Dict[str, Any]:
        miners = len(self.manager.miners)
        total_bonus = sum(b["amount"] for b in self.manager.bonuses.values())
        return {
            "success": True,
            "miners": miners,
            "total_bonuses": total_bonus,
            "early_tiers": self.manager.early_adopter_tiers,
        }


__all__ = ["MiningBonusSystem"]
