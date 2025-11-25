import logging

from .token_supply_manager import TokenSupplyManager

logger = logging.getLogger("xai.blockchain.anti_whale_manager")


class AntiWhaleManager:
    def __init__(
        self,
        token_supply_manager: TokenSupplyManager,
        max_governance_voting_power_percentage: float = 10.0,  # Max 10% of total supply for voting
        max_transaction_size_percentage_of_total_supply: float = 1.0,
    ):  # Max 1% of total supply per transaction

        if not isinstance(token_supply_manager, TokenSupplyManager):
            raise ValueError("token_supply_manager must be an instance of TokenSupplyManager.")
        if not isinstance(max_governance_voting_power_percentage, (int, float)) or not (
            0 < max_governance_voting_power_percentage <= 100
        ):
            raise ValueError("Max governance voting power percentage must be between 0 and 100.")
        if not isinstance(max_transaction_size_percentage_of_total_supply, (int, float)) or not (
            0 < max_transaction_size_percentage_of_total_supply <= 100
        ):
            raise ValueError("Max transaction size percentage must be between 0 and 100.")

        self.token_supply_manager = token_supply_manager
        self.max_governance_voting_power_percentage = max_governance_voting_power_percentage
        self.max_transaction_size_percentage_of_total_supply = (
            max_transaction_size_percentage_of_total_supply
        )
        logger.info(
            "AntiWhaleManager initialized (max voting power %.2f%%, max transaction size %.2f%% of total supply)",
            self.max_governance_voting_power_percentage,
            self.max_transaction_size_percentage_of_total_supply,
        )

    def check_governance_vote(self, voter_address: str, proposed_vote_power: float) -> float:
        """
        Checks and limits the effective voting power of an address.
        Returns the effective voting power after applying the cap.
        """
        total_supply = self.token_supply_manager.get_current_supply()
        if total_supply == 0:
            return 0.0  # No supply, no voting power

        max_allowed_vote_power = total_supply * (
            self.max_governance_voting_power_percentage / 100.0
        )

        effective_vote_power = min(proposed_vote_power, max_allowed_vote_power)

        if effective_vote_power < proposed_vote_power:
            logger.warning(
                "Voter %s proposed %.2f voting power but capped to %.2f due to anti-whale limits",
                voter_address,
                proposed_vote_power,
                effective_vote_power,
            )

        return effective_vote_power

    def check_transaction_size(self, sender_address: str, transaction_amount: float) -> bool:
        """
        Checks if a transaction amount exceeds the maximum allowed percentage of total supply.
        Returns True if the transaction is allowed, False otherwise.
        """
        total_supply = self.token_supply_manager.get_current_supply()
        if total_supply == 0:
            logger.warning(
                "Transaction from %s for %.2f blocked because total supply is zero",
                sender_address,
                transaction_amount,
            )
            return False

        max_allowed_transaction_amount = total_supply * (
            self.max_transaction_size_percentage_of_total_supply / 100.0
        )

        if transaction_amount > max_allowed_transaction_amount:
            logger.warning(
                "Transaction from %s for %.2f exceeds maximum allowed transaction size %.2f (%.2f%% of total supply). Blocked.",
                sender_address,
                transaction_amount,
                max_allowed_transaction_amount,
                self.max_transaction_size_percentage_of_total_supply,
            )
            return False

        logger.info("Transaction from %s for %.2f allowed", sender_address, transaction_amount)
        return True
