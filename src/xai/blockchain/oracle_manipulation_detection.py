from __future__ import annotations

import logging
import time

from ..security.circuit_breaker import CircuitBreaker
from .twap_oracle import TWAPOracle

logger = logging.getLogger("xai.blockchain.oracle_manipulation_detector")

class OracleManipulationDetector:
    def __init__(
        self,
        twap_oracle: TWAPOracle,
        circuit_breaker: CircuitBreaker,
        deviation_threshold_percentage: float = 5.0,
    ):  # 5% deviation
        if not isinstance(twap_oracle, TWAPOracle):
            raise ValueError("twap_oracle must be an instance of TWAPOracle.")
        if not isinstance(circuit_breaker, CircuitBreaker):
            raise ValueError("circuit_breaker must be an instance of CircuitBreaker.")
        if not isinstance(deviation_threshold_percentage, (int, float)) or not (
            0 <= deviation_threshold_percentage < 100
        ):
            raise ValueError("Deviation threshold must be between 0 and 100 (exclusive of 100).")

        self.twap_oracle = twap_oracle
        self.circuit_breaker = circuit_breaker
        self.deviation_threshold_percentage = deviation_threshold_percentage

    def check_for_manipulation(
        self, current_prices: dict[str, float], current_timestamp: int = None
    ) -> bool:
        """
        Checks for oracle manipulation by comparing current prices from multiple sources
        against each other and against the TWAP.

        Args:
            current_prices (dict[str, float]): A dictionary of current prices from different oracle sources
                                                (e.g., {"Chainlink": 100.5, "Uniswap": 101.0}).
            current_timestamp (int): The current timestamp for TWAP calculation. If None, uses current time.

        Returns:
            bool: True if manipulation is suspected, False otherwise.
        """
        if not current_prices:
            logger.warning("No current prices provided for manipulation detection.")
            return False

        current_timestamp = current_timestamp if current_timestamp is not None else int(time.time())

        # 1. Check deviation between current prices
        prices_list = list(current_prices.values())
        if len(prices_list) > 1:
            min_price = min(prices_list)
            max_price = max(prices_list)
            price_range = max_price - min_price
            avg_price = sum(prices_list) / len(prices_list)

            if avg_price > 0:  # Avoid division by zero
                max_deviation_from_avg = (price_range / avg_price) * 100
                if max_deviation_from_avg > self.deviation_threshold_percentage:
                    logger.warning(
                        "Oracle manipulation suspected: deviation %.2f%% exceeds threshold %.2f%%",
                        max_deviation_from_avg,
                        self.deviation_threshold_percentage,
                    )
                    self.circuit_breaker.record_failure()
                    return True

        # 2. Check deviation against TWAP
        twap_price = self.twap_oracle.get_twap(current_timestamp)
        if twap_price > 0:
            for source, price in current_prices.items():
                deviation_from_twap = abs((price - twap_price) / twap_price) * 100
                if deviation_from_twap > self.deviation_threshold_percentage:
                    logger.warning(
                        "Oracle manipulation suspected: %s price %.4f deviates %.2f%% from TWAP %.4f (threshold %.2f%%)",
                        source,
                        price,
                        deviation_from_twap,
                        twap_price,
                        self.deviation_threshold_percentage,
                    )
                    self.circuit_breaker.record_failure()
                    return True

        logger.debug("No oracle manipulation detected.")
        self.circuit_breaker.record_success()  # Record success if no manipulation
        return False
