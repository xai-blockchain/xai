from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from .slashing import (  # Re-using ValidatorStake for RelayerStake
    SlashingManager,
    ValidatorStake,
)

logger = logging.getLogger("xai.blockchain.relayer_staking")

class Relayer:
    def __init__(self, address: str, bonded_amount: int, status: str = "active"):
        if not isinstance(address, str) or not address:
            raise ValueError("Relayer address must be a non-empty string.")
        if not isinstance(bonded_amount, int) or bonded_amount <= 0:
            raise ValueError("Bonded amount must be a positive integer.")
        if status not in ["active", "unbonding", "slashed", "inactive"]:
            raise ValueError("Invalid relayer status.")

        self.address = address
        self.bonded_amount = bonded_amount
        self.status = status
        self.unbonding_start_timestamp: int = 0  # Timestamp when unbonding started

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "bonded_amount": self.bonded_amount,
            "status": self.status,
            "unbonding_start_timestamp": self.unbonding_start_timestamp,
        }

    def __repr__(self):
        return (
            f"Relayer(address='{self.address[:8]}...', bonded={self.bonded_amount}, "
            f"status='{self.status}')"
        )

class RelayerStakingManager:
    DEFAULT_MIN_BOND = 10000
    DEFAULT_UNBONDING_PERIOD_SECONDS = 7 * 24 * 3600  # 7 days

    def __init__(
        self,
        slashing_manager: SlashingManager,
        min_bond: int = DEFAULT_MIN_BOND,
        unbonding_period_seconds: int = DEFAULT_UNBONDING_PERIOD_SECONDS,
        time_provider: Callable[[], int] | None = None,
    ):
        if not isinstance(min_bond, int) or min_bond <= 0:
            raise ValueError("Minimum bond must be a positive integer.")
        if not isinstance(unbonding_period_seconds, int) or unbonding_period_seconds <= 0:
            raise ValueError("Unbonding period must be a positive integer.")

        self.relay_pool: dict[str, Relayer] = {}
        self.slashing_manager = slashing_manager
        self.min_bond = min_bond
        self.unbonding_period_seconds = unbonding_period_seconds
        self._time_provider = time_provider or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def bond_stake(self, relayer_address: str, amount: int) -> Relayer:
        if amount < self.min_bond:
            raise ValueError(
                f"Bonded amount {amount} is less than minimum required bond {self.min_bond}."
            )

        if relayer_address in self.relay_pool:
            relayer = self.relay_pool[relayer_address]
            if relayer.status == "unbonding":
                raise ValueError(
                    f"Relayer {relayer_address} is currently unbonding. Cannot bond more stake."
                )
            relayer.bonded_amount += amount
            relayer.status = "active"
            logger.info(
                "Relayer %s bonded additional %s (total %s).", relayer_address, amount, relayer.bonded_amount
            )
        else:
            relayer = Relayer(relayer_address, amount, "active")
            self.relay_pool[relayer_address] = relayer
            # Also register with slashing manager
            self.slashing_manager.add_validator_stake(ValidatorStake(relayer_address, amount))
            logger.info("New relayer %s bonded %s and is active.", relayer_address, amount)
        return relayer

    def unbond_stake(self, relayer_address: str):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")
        if relayer.status == "unbonding":
            logger.warning("Relayer %s already unbonding", relayer_address)
            return
        if relayer.status == "slashed":
            raise ValueError(f"Relayer {relayer_address} is slashed and cannot unbond.")

        relayer.status = "unbonding"
        relayer.unbonding_start_timestamp = self._current_timestamp()
        logger.info(
            "Relayer %s started unbonding. Release after %s seconds.",
            relayer_address,
            self.unbonding_period_seconds,
        )

    def finalize_unbonding(self, relayer_address: str, current_timestamp: int | None = None):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")
        if relayer.status != "unbonding":
            raise ValueError(f"Relayer {relayer_address} is not in unbonding status.")

        timestamp = current_timestamp if current_timestamp is not None else self._current_timestamp()

        if timestamp >= relayer.unbonding_start_timestamp + self.unbonding_period_seconds:
            # In a real system, funds would be transferred back to the relayer here.
            logger.info(
                "Relayer %s unbonding finalized; %s released",
                relayer_address,
                relayer.bonded_amount,
            )
            relayer.status = "inactive"
            # Remove from slashing manager as well
            self.slashing_manager.remove_validator_stake(relayer_address)
        else:
            remaining_time = (
                relayer.unbonding_start_timestamp + self.unbonding_period_seconds
            ) - timestamp
            logger.info(
                "Relayer %s unbonding incomplete (remaining %s seconds).",
                relayer_address,
                remaining_time,
            )

    def slash_relayer(self, relayer_address: str, offense_type: str):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")

        logger.warning("Slashing relayer %s for %s", relayer_address, offense_type)
        self.slashing_manager.report_malicious_behavior(relayer_address, offense_type)

        # Update relayer's bonded amount based on slashing manager's deduction
        slashed_stake = self.slashing_manager.get_validator_stake(relayer_address)
        if slashed_stake:
            relayer.bonded_amount = slashed_stake.staked_amount
            if relayer.bonded_amount == 0:
                relayer.status = "slashed"
                logger.error("Relayer %s fully slashed.", relayer_address)
            else:
                logger.info("Relayer %s bonded amount reduced to %s.", relayer_address, relayer.bonded_amount)
        else:
            logger.warning("Relayer %s not found in slashing manager after slash attempt.", relayer_address)

    def get_relayer_status(self, relayer_address: str) -> str:
        relayer = self.relay_pool.get(relayer_address)
        return relayer.status if relayer else "not_found"

    def _current_timestamp(self) -> int:
        return int(self._time_provider())
