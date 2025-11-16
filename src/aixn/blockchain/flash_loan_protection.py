from typing import Dict, Any
from src.aixn.blockchain.twap_oracle import TWAPOracle
from src.aixn.blockchain.oracle_manipulation_detection import OracleManipulationDetector
from src.aixn.security.circuit_breaker import CircuitBreaker, CircuitBreakerState
import time


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

        print(
            f"\n--- Checking transaction for flash loan risk: {transaction.get('type', 'unknown')} ---"
        )

        # 1. Check for oracle manipulation
        if self.oracle_detector.check_for_manipulation(current_oracle_prices, current_timestamp):
            print("Flash loan risk detected: Oracle manipulation suspected.")
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
                    print(
                        f"Flash loan risk detected: Excessive price impact ({price_impact:.2f}%) from transaction. "
                        f"Max allowed: {self.max_price_impact_percentage:.2f}%"
                    )
                    self.circuit_breaker.record_failure()
                    return True

        print("No immediate flash loan risk detected for this transaction.")
        self.circuit_breaker.record_success()  # Record success if no risk
        return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Setup TWAP Oracle
    twap_oracle = TWAPOracle(window_size_seconds=300)  # 5-minute TWAP
    sim_time = int(time.time()) - 600  # Start 10 minutes ago
    for _ in range(10):
        twap_oracle.record_price(100.0 + (_ * 0.1), sim_time)
        sim_time += 30

    # Setup Circuit Breaker for general protocol pausing
    protocol_cb = CircuitBreaker(
        name="ProtocolPauseCB", failure_threshold=1, recovery_timeout_seconds=120
    )

    # Setup Oracle Manipulation Detector
    oracle_detector = OracleManipulationDetector(
        twap_oracle, protocol_cb, deviation_threshold_percentage=2.0
    )

    # Setup Flash Loan Protection Manager
    flash_loan_manager = FlashLoanProtectionManager(
        twap_oracle, oracle_detector, protocol_cb, max_price_impact_percentage=1.0
    )  # 1% max price impact

    # Simulate current market conditions
    current_asset_liquidity = 1000000.0  # 1,000,000 units of liquidity
    current_oracle_prices = {"Chainlink": 101.5, "Uniswap": 101.6, "Band": 101.4}

    print("--- Scenario 1: Normal Transaction ---")
    normal_tx = {"type": "swap", "asset": "TokenX", "amount": 1000.0}
    is_risky = flash_loan_manager.check_transaction_for_flash_loan_risk(
        normal_tx, current_oracle_prices, current_asset_liquidity, sim_time
    )
    print(f"Is normal transaction risky? {is_risky}")
    print(f"Protocol Circuit Breaker State: {protocol_cb.state}\n")

    print("--- Scenario 2: Transaction with High Price Impact ---")
    large_tx = {"type": "swap", "asset": "TokenX", "amount": 500000.0}  # 50% of liquidity
    is_risky = flash_loan_manager.check_transaction_for_flash_loan_risk(
        large_tx, current_oracle_prices, current_asset_liquidity, sim_time
    )
    print(f"Is large transaction risky? {is_risky}")
    print(f"Protocol Circuit Breaker State: {protocol_cb.state}\n")

    print("--- Scenario 3: Oracle Manipulation Detected ---")
    manipulated_prices = {"Chainlink": 101.5, "Uniswap": 108.0, "Band": 101.4}  # Manipulated price
    another_normal_tx = {"type": "borrow", "asset": "TokenY", "amount": 5000.0}
    is_risky = flash_loan_manager.check_transaction_for_flash_loan_risk(
        another_normal_tx, manipulated_prices, current_asset_liquidity, sim_time
    )
    print(f"Is transaction with manipulated oracle risky? {is_risky}")
    print(f"Protocol Circuit Breaker State: {protocol_cb.state}\n")

    print("--- Scenario 4: Protocol Paused due to previous risk ---")
    # Since failure_threshold is 1, the CB should be OPEN from Scenario 2 or 3
    if protocol_cb.state == CircuitBreakerState.OPEN:
        print("Protocol is paused. No new transactions will be processed.")
    else:
        print("Protocol is not paused.")
