from typing import List, Dict, Any
from src.aixn.blockchain.twap_oracle import TWAPOracle
from src.aixn.security.circuit_breaker import CircuitBreaker, CircuitBreakerState
import time


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
        self, current_prices: Dict[str, float], current_timestamp: int = None
    ) -> bool:
        """
        Checks for oracle manipulation by comparing current prices from multiple sources
        against each other and against the TWAP.

        Args:
            current_prices (Dict[str, float]): A dictionary of current prices from different oracle sources
                                                (e.g., {"Chainlink": 100.5, "Uniswap": 101.0}).
            current_timestamp (int): The current timestamp for TWAP calculation. If None, uses current time.

        Returns:
            bool: True if manipulation is suspected, False otherwise.
        """
        if not current_prices:
            print("No current prices provided for manipulation detection.")
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
                    print(
                        f"!!! ORACLE MANIPULATION SUSPECTED: High deviation between oracle sources. "
                        f"Max deviation: {max_deviation_from_avg:.2f}% (Threshold: {self.deviation_threshold_percentage:.2f}%)"
                    )
                    self.circuit_breaker.record_failure()
                    return True

        # 2. Check deviation against TWAP
        twap_price = self.twap_oracle.get_twap(current_timestamp)
        if twap_price > 0:
            for source, price in current_prices.items():
                deviation_from_twap = abs((price - twap_price) / twap_price) * 100
                if deviation_from_twap > self.deviation_threshold_percentage:
                    print(
                        f"!!! ORACLE MANIPULATION SUSPECTED: Price from {source} ({price:.4f}) deviates significantly from TWAP ({twap_price:.4f}). "
                        f"Deviation: {deviation_from_twap:.2f}% (Threshold: {self.deviation_threshold_percentage:.2f}%)"
                    )
                    self.circuit_breaker.record_failure()
                    return True

        print("No oracle manipulation detected.")
        self.circuit_breaker.record_success()  # Record success if no manipulation
        return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Setup TWAP Oracle
    twap_oracle = TWAPOracle(window_size_seconds=300)  # 5-minute TWAP

    # Simulate some initial price data for TWAP
    sim_time = int(time.time()) - 600  # Start 10 minutes ago
    for _ in range(10):
        twap_oracle.record_price(100.0 + (_ * 0.1), sim_time)
        sim_time += 30  # Every 30 seconds

    # Setup Circuit Breaker
    manipulation_cb = CircuitBreaker(
        name="OracleManipulationCB", failure_threshold=1, recovery_timeout_seconds=60
    )

    # Setup Detector
    detector = OracleManipulationDetector(
        twap_oracle, manipulation_cb, deviation_threshold_percentage=2.0
    )  # 2% threshold

    print("--- Scenario 1: Normal Operation ---")
    current_prices_normal = {"Chainlink": 101.5, "Uniswap": 101.6, "Band": 101.4}
    is_manipulated = detector.check_for_manipulation(current_prices_normal, sim_time)
    print(f"Manipulation detected: {is_manipulated}")
    print(f"Circuit Breaker State: {manipulation_cb.state}\n")

    print("--- Scenario 2: High Deviation Between Oracles ---")
    current_prices_deviated = {
        "Chainlink": 101.5,
        "Uniswap": 105.0,  # Significantly higher
        "Band": 101.4,
    }
    is_manipulated = detector.check_for_manipulation(current_prices_deviated, sim_time)
    print(f"Manipulation detected: {is_manipulated}")
    print(f"Circuit Breaker State: {manipulation_cb.state}\n")

    print("--- Scenario 3: Price deviates from TWAP ---")
    # Record a new price that will significantly shift the TWAP
    twap_oracle.record_price(150.0, sim_time + 10)  # A sudden spike

    current_prices_twap_deviated = {"Chainlink": 102.0, "Uniswap": 102.1, "Band": 102.0}
    is_manipulated = detector.check_for_manipulation(current_prices_twap_deviated, sim_time + 20)
    print(f"Manipulation detected: {is_manipulated}")
    print(f"Circuit Breaker State: {manipulation_cb.state}\n")

    print("--- Scenario 4: Circuit Breaker in OPEN state ---")
    # Since failure_threshold is 1, the CB should be OPEN from Scenario 2 or 3
    is_manipulated = detector.check_for_manipulation(current_prices_normal, sim_time + 30)
    print(f"Manipulation detected: {is_manipulated}")
    print(f"Circuit Breaker State: {manipulation_cb.state}\n")
