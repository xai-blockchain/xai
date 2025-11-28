import logging
from typing import Dict

logger = logging.getLogger("xai.blockchain.mev_redistributor")


class MEVRedistributor:
    def __init__(self, redistribution_percentage: float = 50.0):
        if not isinstance(redistribution_percentage, (int, float)) or not (
            0 <= redistribution_percentage <= 100
        ):
            raise ValueError("Redistribution percentage must be between 0 and 100.")

        self.redistribution_percentage = redistribution_percentage
        self.total_mev_captured = 0.0
        self.total_mev_redistributed = 0.0
        logger.info(
            "MEVRedistributor initialized with redistribution percentage %.2f",
            self.redistribution_percentage,
        )

    def capture_mev(self, amount: float):
        """Simulates capturing MEV from a block."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("MEV amount must be a non-negative number.")
        self.total_mev_captured += amount
        logger.info("Captured %.2f MEV (total captured %.2f)", amount, self.total_mev_captured)

    def redistribute_mev(self, users: Dict[str, float]) -> Dict[str, float]:
        """
        Redistributes a portion of the captured MEV to users based on their proportional share.
        'users' is a dictionary of {user_address: proportional_share_factor}.
        Returns a dictionary of {user_address: redistributed_amount}.
        """
        if not users:
            logger.warning("Redistribution skipped: no users provided")
            return {}

        mev_to_redistribute = self.total_mev_captured * (self.redistribution_percentage / 100.0)

        if mev_to_redistribute <= 0:
            logger.warning(
                "Redistribution skipped: no MEV available (captured %.2f, percentage %.2f)",
                self.total_mev_captured,
                self.redistribution_percentage,
            )
            return {}

        total_share_factors = sum(users.values())
        if total_share_factors <= 0:
            logger.warning("Redistribution skipped: total user share factors are zero")
            return {}

        redistributed_amounts: Dict[str, float] = {}
        for user_address, share_factor in users.items():
            if share_factor > 0:
                amount_for_user = (share_factor / total_share_factors) * mev_to_redistribute
                redistributed_amounts[user_address] = amount_for_user
                self.total_mev_redistributed += amount_for_user
                logger.info(
                    "Redistributed %.2f MEV to %s (total redistributed %.2f)",
                    amount_for_user,
                    user_address,
                    self.total_mev_redistributed,
                )

        self.total_mev_captured -= mev_to_redistribute  # Deduct redistributed amount from captured
        logger.info(
            "Redistribution complete (redistributed %.2f, remaining captured %.2f)",
            mev_to_redistribute,
            self.total_mev_captured,
        )
        return redistributed_amounts
