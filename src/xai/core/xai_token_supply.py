from __future__ import annotations

"""
XAI Blockchain - XAI Token Supply Management

Manages the total supply, circulating supply, and burning mechanisms of the XAI token.
"""

from typing import Any

from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.xai_token_manager import XAITokenManager, get_xai_token_manager

class XAITokenSupply:
    """
    Manages the supply of XAI tokens, including minting, burning, and tracking.
    """

    def __init__(
        self,
        token_manager: XAITokenManager | None = None,
        logger: StructuredLogger | None = None,
    ):
        self.token_manager = token_manager or get_xai_token_manager()
        self.logger = logger or get_structured_logger()
        self.burned_tokens = 0.0
        self.logger.info("XAITokenSupply initialized.")

    def get_total_supply(self) -> float:
        """
        Returns the total minted supply of XAI tokens.
        """
        return self.token_manager.get_total_supply()

    def get_circulating_supply(self) -> float:
        """
        Calculates and returns the circulating supply of XAI tokens.
        This excludes tokens held in vesting schedules or burned.
        """
        return self.token_manager.get_token_metrics()["circulating_supply"] - self.burned_tokens

    def get_supply_cap(self) -> float:
        """
        Returns the maximum allowed supply of XAI tokens.
        """
        return self.token_manager.get_supply_cap()

    def burn_tokens(self, address: str, amount: float) -> bool:
        """
        Burns a specified amount of tokens from an address.

        Args:
            address: The address from which to burn tokens.
            amount: The amount of tokens to burn.

        Returns:
            True if burning was successful, False otherwise.
        """
        if amount <= 0:
            self.logger.warn(
                "Attempted to burn non-positive amount.", address=address, amount=amount
            )
            return False

        current_balance = self.token_manager.get_balance(address)
        if current_balance < amount:
            self.logger.warn(
                f"Insufficient balance to burn {amount} XAI from {address}.",
                address=address,
                amount=amount,
                balance=current_balance,
            )
            return False

        # Deduct from balance
        self.token_manager.xai_token.balances[address] -= amount
        self.burned_tokens += amount
        self.logger.info(
            f"Burned {amount} XAI from {address}.",
            address=address,
            amount=amount,
            new_balance=self.token_manager.get_balance(address),
            total_burned=self.burned_tokens,
        )
        return True

    def get_burned_tokens(self) -> float:
        """
        Returns the total amount of XAI tokens that have been burned.
        """
        return self.burned_tokens

    def get_supply_metrics(self) -> dict[str, Any]:
        """
        Returns a comprehensive set of supply-related metrics.
        """
        token_metrics = self.token_manager.get_token_metrics()
        return {
            "total_supply": token_metrics["total_supply"],
            "supply_cap": token_metrics["supply_cap"],
            "circulating_supply": self.get_circulating_supply(),
            "burned_tokens": self.burned_tokens,
            "vested_tokens": token_metrics["total_supply"]
            - token_metrics[
                "circulating_supply"
            ],  # This is the non-circulating part due to vesting
        }

# Global instance for convenience
_global_xai_token_supply = None

def get_xai_token_supply(
    token_manager: XAITokenManager | None = None, logger: StructuredLogger | None = None
) -> XAITokenSupply:
    """
    Get global XAITokenSupply instance.
    """
    global _global_xai_token_supply
    if _global_xai_token_supply is None:
        _global_xai_token_supply = XAITokenSupply(token_manager, logger)
    return _global_xai_token_supply
