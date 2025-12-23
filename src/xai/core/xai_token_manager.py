from __future__ import annotations

"""
XAI Blockchain - XAI Token Manager

Manages the core XAI token functionalities, including supply, balances, and vesting.
"""

import time
from typing import Any

from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.xai_token import XAIToken


class XAITokenManager:
    """
    Manages the XAI token, its supply, and individual balances.
    """

    def __init__(
        self,
        initial_supply: float = 0,
        supply_cap: float = 121_000_000,
        logger: StructuredLogger | None = None,
    ):
        self.xai_token = XAIToken(initial_supply, supply_cap)
        self.logger = logger or get_structured_logger()
        self.logger.info(
            "XAITokenManager initialized.", initial_supply=initial_supply, supply_cap=supply_cap
        )

    def mint_tokens(self, address: str, amount: float) -> bool:
        """
        Mints new XAI tokens and assigns them to an address.

        Args:
            address: The recipient address.
            amount: The amount of tokens to mint.

        Returns:
            True if minting was successful, False otherwise.
        """
        if amount <= 0:
            self.logger.warn(
                "Attempted to mint non-positive amount.", address=address, amount=amount
            )
            return False

        if self.xai_token.mint(address, amount):
            self.logger.info(
                f"Minted {amount} XAI to {address}.",
                address=address,
                amount=amount,
                new_total_supply=self.xai_token.total_supply,
            )
            return True
        else:
            self.logger.error(
                f"Failed to mint {amount} XAI to {address}. Supply cap reached or other error.",
                address=address,
                amount=amount,
            )
            return False

    def transfer_tokens(self, sender: str, recipient: str, amount: float) -> bool:
        """
        Transfers XAI tokens from one address to another.

        Args:
            sender: The sender's address.
            recipient: The recipient's address.
            amount: The amount of tokens to transfer.

        Returns:
            True if transfer was successful, False otherwise.
        """
        if amount <= 0:
            self.logger.warn(
                "Attempted to transfer non-positive amount.",
                sender=sender,
                recipient=recipient,
                amount=amount,
            )
            return False

        if self.xai_token.balances.get(sender, 0) < amount:
            self.logger.warn(
                f"Insufficient balance for transfer from {sender}.",
                sender=sender,
                recipient=recipient,
                amount=amount,
                sender_balance=self.xai_token.balances.get(sender, 0),
            )
            return False

        self.xai_token.balances[sender] -= amount
        self.xai_token.balances[recipient] = self.xai_token.balances.get(recipient, 0) + amount
        self.logger.info(
            f"Transferred {amount} XAI from {sender} to {recipient}.",
            sender=sender,
            recipient=recipient,
            amount=amount,
        )
        return True

    def get_balance(self, address: str) -> float:
        """
        Retrieves the current balance of an address.

        Args:
            address: The address to query.

        Returns:
            The balance of the address.
        """
        return self.xai_token.balances.get(address, 0)

    def get_total_supply(self) -> float:
        """
        Returns the total minted supply of XAI tokens.
        """
        return self.xai_token.total_supply

    def get_supply_cap(self) -> float:
        """
        Returns the maximum allowed supply of XAI tokens.
        """
        return self.xai_token.supply_cap

    def get_token_metrics(self) -> dict[str, Any]:
        """
        Returns key metrics of the XAI token.
        """
        return self.xai_token.get_token_metrics()

    def create_vesting_schedule(
        self, address: str, amount: float, cliff_duration: int, total_duration: int
    ) -> bool:
        """
        Creates a vesting schedule for a given address.
        """
        if self.xai_token.create_vesting_schedule(address, amount, cliff_duration, total_duration):
            self.logger.info(
                f"Vesting schedule created for {address} for {amount} XAI.",
                address=address,
                amount=amount,
            )
            return True
        else:
            self.logger.error(
                f"Failed to create vesting schedule for {address}.", address=address, amount=amount
            )
            return False

    def get_vesting_status(self, address: str) -> dict[str, Any] | None:
        """
        Retrieves the vesting status for an address.
        """
        return self.xai_token.vesting_schedules.get(address)

# Global instance for convenience
_global_xai_token_manager = None

def get_xai_token_manager(
    initial_supply: float = 0,
    supply_cap: float = 121_000_000,
    logger: StructuredLogger | None = None,
) -> XAITokenManager:
    """
    Get global XAITokenManager instance.
    """
    global _global_xai_token_manager
    if _global_xai_token_manager is None:
        _global_xai_token_manager = XAITokenManager(initial_supply, supply_cap, logger)
    return _global_xai_token_manager
