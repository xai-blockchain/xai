from typing import Dict, List, Any
import time
from src.aixn.security.circuit_breaker import CircuitBreaker, CircuitBreakerState

class WashTradingDetector:
    def __init__(self, circuit_breaker: CircuitBreaker, round_trip_time_window_seconds: int = 300):
        if not isinstance(circuit_breaker, CircuitBreaker):
            raise ValueError("circuit_breaker must be an instance of CircuitBreaker.")
        if not isinstance(round_trip_time_window_seconds, int) or round_trip_time_window_seconds <= 0:
            raise ValueError("Round trip time window must be a positive integer.")

        self.circuit_breaker = circuit_breaker
        self.round_trip_time_window_seconds = round_trip_time_window_seconds
        # Stores trades: {trade_id: {"buyer": str, "seller": str, "asset": str, "amount": float, "price": float, "timestamp": int}}
        self.trade_history: List[Dict[str, Any]] = []
        self._trade_id_counter = 0

    def record_trade(self, buyer_address: str, seller_address: str, asset: str, amount: float, price: float):
        """Records a new trade."""
        if not buyer_address or not seller_address or not asset:
            raise ValueError("Buyer, seller, and asset cannot be empty.")
        if amount <= 0 or price <= 0:
            raise ValueError("Amount and price must be positive.")

        self._trade_id_counter += 1
        trade_id = f"trade_{self._trade_id_counter}"
        trade = {
            "trade_id": trade_id,
            "buyer": buyer_address,
            "seller": seller_address,
            "asset": asset,
            "amount": amount,
            "price": price,
            "timestamp": int(time.time())
        }
        self.trade_history.append(trade)
        print(f"Recorded trade {trade_id}: {asset} {amount} @ {price} from {seller_address} to {buyer_address}")

    def detect_self_trading(self) -> bool:
        """
        Detects self-trading where the buyer and seller are the same address.
        """
        print("\n--- Detecting Self-Trading ---")
        for trade in self.trade_history:
            if trade["buyer"] == trade["seller"]:
                print(f"!!! WASH TRADING DETECTED: Self-trading in trade {trade['trade_id']} by {trade['buyer']}.")
                self.circuit_breaker.record_failure()
                return True
        print("No self-trading detected.")
        self.circuit_breaker.record_success()
        return False

    def detect_round_trip_trading(self) -> bool:
        """
        Detects round-trip trading where an asset is sold and then bought back
        by the same entity (or a related entity) within a short time window.
        This is a simplified conceptual model.
        """
        print("\n--- Detecting Round-Trip Trading ---")
        current_time = int(time.time())
        
        # Group trades by asset and then by participant
        asset_trades: Dict[str, List[Dict[str, Any]]] = {}
        for trade in self.trade_history:
            asset_trades.setdefault(trade["asset"], []).append(trade)

        for asset, trades in asset_trades.items():
            # Filter trades within the time window
            recent_trades = [t for t in trades if (current_time - t["timestamp"]) <= self.round_trip_time_window_seconds]
            
            # Sort by timestamp to check sequence
            recent_trades.sort(key=lambda x: x["timestamp"])

            for i in range(len(recent_trades)):
                trade1 = recent_trades[i]
                for j in range(i + 1, len(recent_trades)):
                    trade2 = recent_trades[j]

                    # Check for a sell followed by a buy of the same asset by the same entity
                    # (or a buy followed by a sell)
                    if (trade1["seller"] == trade2["buyer"] and trade1["buyer"] == trade2["seller"] and
                        trade1["asset"] == trade2["asset"] and
                        (trade2["timestamp"] - trade1["timestamp"]) <= self.round_trip_time_window_seconds):
                        print(f"!!! WASH TRADING DETECTED: Round-trip trading of {asset} between {trade1['seller']} and {trade1['buyer']} in trades {trade1['trade_id']} and {trade2['trade_id']}.")
                        self.circuit_breaker.record_failure()
                        return True
        print("No round-trip trading detected.")
        self.circuit_breaker.record_success()
        return False

# Example Usage (for testing purposes)
if __name__ == "__main__":
    cb = CircuitBreaker(name="WashTradingCB", failure_threshold=1, recovery_timeout_seconds=60)
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=10) # 10-second window for example

    user_a = "0xUserA"
    user_b = "0xUserB"
    user_c = "0xUserC"
    asset_eth = "ETH"
    asset_usdc = "USDC"

    print("--- Scenario 1: Normal Trades ---")
    detector.record_trade(user_a, user_b, asset_eth, 1.0, 2000.0)
    detector.record_trade(user_b, user_c, asset_usdc, 500.0, 1.0)
    print(f"Wash trading detected: {detector.detect_self_trading() or detector.detect_round_trip_trading()}")
    print(f"Circuit Breaker State: {cb.state}\n")

    print("--- Scenario 2: Self-Trading ---")
    detector.record_trade(user_a, user_a, asset_eth, 0.5, 2005.0)
    print(f"Wash trading detected: {detector.detect_self_trading() or detector.detect_round_trip_trading()}")
    print(f"Circuit Breaker State: {cb.state}\n")

    print("--- Scenario 3: Round-Trip Trading ---")
    # Reset CB for this scenario
    cb_rt = CircuitBreaker(name="WashTradingCB_RT", failure_threshold=1, recovery_timeout_seconds=60)
    detector_rt = WashTradingDetector(cb_rt, round_trip_time_window_seconds=10)

    detector_rt.record_trade(user_a, user_b, asset_eth, 1.0, 2010.0) # User A buys from B
    time.sleep(2)
    detector_rt.record_trade(user_b, user_a, asset_eth, 1.0, 2011.0) # User B buys back from A (round trip)
    print(f"Wash trading detected: {detector_rt.detect_self_trading() or detector_rt.detect_round_trip_trading()}")
    print(f"Circuit Breaker State: {cb_rt.state}\n")

    print("--- Scenario 4: Round-Trip Trading (outside time window) ---")
    # Reset CB for this scenario
    cb_rt_long = CircuitBreaker(name="WashTradingCB_RT_Long", failure_threshold=1, recovery_timeout_seconds=60)
    detector_rt_long = WashTradingDetector(cb_rt_long, round_trip_time_window_seconds=5)

    detector_rt_long.record_trade(user_a, user_b, asset_eth, 1.0, 2020.0)
    time.sleep(6) # Outside 5-second window
    detector_rt_long.record_trade(user_b, user_a, asset_eth, 1.0, 2021.0)
    print(f"Wash trading detected: {detector_rt_long.detect_self_trading() or detector_rt_long.detect_round_trip_trading()}")
    print(f"Circuit Breaker State: {cb_rt_long.state}\n")
