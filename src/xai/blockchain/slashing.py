import logging
from typing import Dict, Any


class ValidatorStake:
    def __init__(self, address: str, staked_amount: int):
        if not isinstance(address, str) or not address:
            raise ValueError("Validator address must be a non-empty string.")
        if not isinstance(staked_amount, int) or staked_amount <= 0:
            raise ValueError("Staked amount must be a positive integer.")
        self.address = address
        self.staked_amount = staked_amount
        self.slashed_amount = 0

    def deduct_stake(self, amount: int):
        if amount < 0:
            raise ValueError("Deduction amount cannot be negative.")
        if self.staked_amount < amount:
            amount = self.staked_amount  # Cannot deduct more than available stake
        self.staked_amount -= amount
        self.slashed_amount += amount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "staked_amount": self.staked_amount,
            "slashed_amount": self.slashed_amount,
        }

    def __repr__(self):
        return f"ValidatorStake(address='{self.address[:8]}...', staked={self.staked_amount}, slashed={self.slashed_amount})"


class SlashingManager:
    OFFENSE_PENALTIES = {
        "double_signing": 0.25,  # 25% of stake
        "offline_long_period": 0.05,  # 5% of stake
        "invalid_attestation": 0.10,  # 10% of stake
        "collusion_bridge_funds": 1.00,  # 100% of stake (full slash)
    }

    def __init__(self):
        self.validator_stakes: Dict[str, ValidatorStake] = {}
        self.slashed_funds_treasury = 0  # Represents funds collected from slashing
        self.logger = logging.getLogger("xai.blockchain.slashing")

    def add_validator_stake(self, validator_stake: ValidatorStake):
        if validator_stake.address in self.validator_stakes:
            self.logger.warning("Stake for %s already exists. Updating.", validator_stake.address)
        self.validator_stakes[validator_stake.address] = validator_stake

    def remove_validator_stake(self, address: str):
        self.validator_stakes.pop(address, None)

    def report_malicious_behavior(self, validator_address: str, offense_type: str):
        if validator_address not in self.validator_stakes:
            self.logger.warning("Validator %s not found in stake registry.", validator_address)
            return

        if offense_type not in self.OFFENSE_PENALTIES:
            self.logger.warning("Unknown offense type '%s'.", offense_type)
            return

        validator = self.validator_stakes[validator_address]
        penalty_percentage = self.OFFENSE_PENALTIES[offense_type]

        slash_amount = int(validator.staked_amount * penalty_percentage)
        if (
            slash_amount == 0 and penalty_percentage > 0
        ):  # Ensure at least 1 unit is slashed if penalty > 0
            slash_amount = 1 if validator.staked_amount > 0 else 0

        if slash_amount > 0:
            validator.deduct_stake(slash_amount)
            self.slashed_funds_treasury += slash_amount
            self.logger.warning(
                "Validator %s slashed %s for '%s'. Treasury=%s",
                validator_address,
                slash_amount,
                offense_type,
                self.slashed_funds_treasury,
            )
        else:
            self.logger.info("No stake to slash for validator %s.", validator_address)

    def get_validator_stake(self, address: str) -> ValidatorStake:
        return self.validator_stakes.get(address)

    def get_slashed_funds_treasury(self) -> int:
        return self.slashed_funds_treasury

