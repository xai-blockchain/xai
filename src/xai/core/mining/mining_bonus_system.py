"""Adapter around the mining bonus manager for node orchestration."""

from __future__ import annotations

from typing import Any

from xai.core.mining.mining_bonuses import MiningBonusManager


class MiningBonusSystem:
    """Facade used by API routes to access bonus data."""

    def __init__(self) -> None:
        self.manager = MiningBonusManager()

    def register_miner(self, address: str) -> dict[str, Any]:
        return self.manager.register_miner(address)

    def get_bonus_stats(self) -> dict[str, Any]:
        miners = len(self.manager.miners)
        total_bonus = self.manager.get_total_awarded_amount()
        return {
            "success": True,
            "miners": miners,
            "total_bonuses": total_bonus,
            "early_tiers": self.manager.early_adopter_tiers,
            "bonus_cap": self.manager.max_bonus_supply,
            "bonus_remaining": self.manager.get_bonus_supply_remaining(),
        }

__all__ = ["MiningBonusSystem"]
