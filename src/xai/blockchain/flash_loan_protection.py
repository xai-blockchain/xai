import logging
from typing import Dict, Any
import time

from .twap_oracle import TWAPOracle
from .oracle_manipulation_detection import OracleManipulationDetector
from ..security.circuit_breaker import CircuitBreaker

logger = logging.getLogger("xai.blockchain.flash_loan_protection")


class FlashLoanProtectionManager:
    def __init__(
        self,
        twap_oracle: TWAPOracle,
        oracle_detector: OracleManipulationDetector,
        circuit_breaker: CircuitBreaker,
        max_price_impact_percentage: float = 5.0,
    ):
        if not isinstance(twap_oracle, TWAPOracle):
            raise ValueError("twap_oracle must be an instance of TWAPOracle.")
        if not isinstance(oracle_detector, OracleManipulationDetector):
            raise ValueError("oracle_detector must be an instance of OracleManipulationDetector.")
        if not isinstance(circuit_breaker, CircuitBreaker):
            raise ValueError("circuit_breaker must be an instance of CircuitBreaker.")
        if not isinstance(max_price_impact_percentage, (int, float)) or not (
            0 <= max_price_impact_percentage < 100
        ):
            raise ValueError(
                "Max price impact percentage must be between 0 and 100 (exclusive of 100)."
            )

        self.twap_oracle = twap_oracle
        self.oracle_detector = oracle_detector
        self.circuit_breaker = circuit_breaker
        self.max_price_impact_percentage = max_price_impact_percentage

    def _simulate_price_impact(
        self, current_price: float, trade_volume: float, liquidity: float
    ) -> float:
        """
        A very simplified simulation of price impact.
        In a real AMM, this would be based on the constant product formula (x*y=k).
        Here, we assume a linear impact for demonstration.
        """
        if liquidity <= 0:
            return 0.0  # Infinite price impact if no liquidity

        # Assume 1% of liquidity moved causes X% price impact
        # This is a placeholder, real AMM math is more complex
        impact_factor = (trade_volume / liquidity) * 100
        simulated_new_price = current_price * (1 - (impact_factor / 200))  # Arbitrary impact model
        return simulated_new_price

    def check_transaction_for_flash_loan_risk(
        self,
        transaction: Dict[str, Any],
        current_oracle_prices: Dict[str, float],
        asset_liquidity: float,
        current_timestamp: int = None,
    ) -> bool:
        """
        Checks a transaction for potential flash loan attack indicators.

        Args:
            transaction (Dict[str, Any]): The transaction details (e.g., {"type": "swap", "amount": 1000000, ...}).
            current_oracle_prices (Dict[str, float]): Current prices from various oracles.
            asset_liquidity (float): The total liquidity available for the asset being traded/manipulated.
            current_timestamp (int): The current timestamp.

        Returns:
            bool: True if flash loan risk is detected, False otherwise.
        """
        current_timestamp = current_timestamp if current_timestamp is not None else int(time.time())

        logger.debug(
            "Checking transaction for flash loan risk: %s", transaction.get("type", "unknown")
        )

        # 1. Check for oracle manipulation
        if self.oracle_detector.check_for_manipulation(current_oracle_prices, current_timestamp):
            logger.warning("Flash loan risk detected: oracle manipulation suspected")
            self.circuit_breaker.record_failure()
            return True

        # 2. Check for excessive price impact from the transaction
        if "amount" in transaction and "asset" in transaction:
            current_twap_price = self.twap_oracle.get_twap(current_timestamp)
            if current_twap_price > 0 and asset_liquidity > 0:
                simulated_new_price = self._simulate_price_impact(
                    current_twap_price, transaction["amount"], asset_liquidity
                )
                price_impact = (
                    abs((simulated_new_price - current_twap_price) / current_twap_price) * 100
                )

                if price_impact > self.max_price_impact_percentage:
                    logger.warning(
                        "Flash loan risk detected: price impact %.2f%% exceeds max %.2f%%",
                        price_impact,
                        self.max_price_impact_percentage,
                    )
                    self.circuit_breaker.record_failure()
                    return True

        logger.info("No immediate flash loan risk detected.")
        self.circuit_breaker.record_success()  # Record success if no risk
        return False
