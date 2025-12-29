from __future__ import annotations

"""
XAI Blockchain - XAI Token Vesting Management

Manages vesting schedules for XAI tokens, ensuring tokens are released over time.
"""

import time
from typing import Any

from xai.core.api.structured_logger import StructuredLogger, get_structured_logger
from xai.core.governance.xai_token_manager import XAITokenManager, get_xai_token_manager


class XAITokenVesting:
    """
    Manages vesting schedules for XAI tokens.
    """

    def __init__(
        self,
        token_manager: XAITokenManager | None = None,
        logger: StructuredLogger | None = None,
    ):
        self.token_manager = token_manager or get_xai_token_manager()
        self.logger = logger or get_structured_logger()
        self.logger.info("XAITokenVesting initialized.")

    def create_vesting_schedule(
        self, address: str, amount: float, cliff_duration: int, total_duration: int
    ) -> bool:
        """
        Creates a vesting schedule for a given address.

        Args:
            address: The address for which to create the vesting schedule.
            amount: The total amount of tokens to vest.
            cliff_duration: The duration (in seconds) before vesting begins.
            total_duration: The total duration (in seconds) over which tokens will vest.

        Returns:
            True if the vesting schedule was created successfully, False otherwise.
        """
        if amount <= 0 or cliff_duration < 0 or total_duration <= cliff_duration:
            self.logger.warn(
                "Invalid parameters for vesting schedule creation.",
                address=address,
                amount=amount,
                cliff_duration=cliff_duration,
                total_duration=total_duration,
            )
            return False

        if self.token_manager.create_vesting_schedule(
            address, amount, cliff_duration, total_duration
        ):
            self.logger.info(
                f"Vesting schedule created for {address} for {amount} XAI.",
                address=address,
                amount=amount,
                cliff_duration=cliff_duration,
                total_duration=total_duration,
            )
            return True
        else:
            self.logger.error(
                f"Failed to create vesting schedule for {address}.", address=address, amount=amount
            )
            return False

    def get_vesting_status(self, address: str) -> dict[str, Any] | None:
        """
        Retrieves the current vesting status for an address.

        Args:
            address: The address to query.

        Returns:
            A dictionary containing vesting details, or None if no schedule exists.
        """
        return self.token_manager.get_vesting_status(address)

    def release_vested_tokens(self, address: str) -> float:
        """
        Calculates and releases any newly vested tokens to the address's balance.

        Args:
            address: The address for which to release tokens.

        Returns:
            The amount of tokens released.
        """
        schedule = self.token_manager.get_vesting_status(address)
        if not schedule:
            return 0.0

        current_time = time.time()
        if current_time < schedule["cliff_end"]:
            return 0.0  # Still in cliff period

        total_vested_amount = schedule["amount"]
        total_duration = schedule["end_date"] - (
            schedule["cliff_end"] - schedule["cliff_duration"]
        )  # Recalculate total duration from start of vesting

        if total_duration <= 0:  # Avoid division by zero if total_duration is somehow invalid
            return 0.0

        time_elapsed_since_cliff = current_time - schedule["cliff_end"]

        # Calculate the proportion of tokens that should have vested by now
        vested_proportion = min(1.0, time_elapsed_since_cliff / total_duration)

        # Total amount that should have vested
        should_have_vested = total_vested_amount * vested_proportion

        # Amount to release now
        to_release = should_have_vested - schedule["released"]

        if to_release > 0:
            # Update balance and released amount
            self.token_manager.transfer_tokens(
                "vesting_contract_address", address, to_release
            )  # Assuming a generic vesting contract address
            schedule["released"] += to_release
            self.logger.info(
                f"Released {to_release} vested XAI to {address}.",
                address=address,
                released_amount=to_release,
            )
            return to_release
        return 0.0

    def get_total_vested_amount(self) -> float:
        """
        Returns the total amount of tokens currently under vesting across all schedules.
        """
        total = 0.0
        for schedule in self.token_manager.xai_token.vesting_schedules.values():
            total += schedule["amount"] - schedule["released"]
        return total

# Global instance for convenience
_global_xai_token_vesting = None

def get_xai_token_vesting(
    token_manager: XAITokenManager | None = None, logger: StructuredLogger | None = None
) -> XAITokenVesting:
    """
    Get global XAITokenVesting instance.
    """
    global _global_xai_token_vesting
    if _global_xai_token_vesting is None:
        _global_xai_token_vesting = XAITokenVesting(token_manager, logger)
    return _global_xai_token_vesting
