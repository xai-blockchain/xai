import math

from xai.blockchain.twap_oracle import TWAPOracle
from xai.blockchain.oracle_manipulation_detection import OracleManipulationDetector
from xai.blockchain.flash_loan_protection import FlashLoanProtectionManager
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


def _seed_oracle(oracle: TWAPOracle, base_price: float = 100.0, points: int = 5, start: int = 100):
    timestamp = start
    for _ in range(points):
        oracle.record_price(base_price, timestamp)
        timestamp += 30


def test_twap_oracle_computes_average():
    oracle = TWAPOracle(window_size_seconds=120)
    oracle.record_price(100.0, timestamp=100)
    oracle.record_price(200.0, timestamp=160)
    twap = oracle.get_twap(current_timestamp=220)
    assert math.isclose(twap, 150.0, rel_tol=1e-6)

    # Advance past the window to ensure cleanup
    twap_empty = oracle.get_twap(current_timestamp=500)
    assert twap_empty == 0.0


def test_oracle_manipulation_detector_trips_on_deviation():
    circuit = CircuitBreaker("oracle-detector", failure_threshold=1, recovery_timeout_seconds=10)
    oracle = TWAPOracle(window_size_seconds=300)
    _seed_oracle(oracle)
    detector = OracleManipulationDetector(oracle, circuit, deviation_threshold_percentage=2.0)

    safe_prices = {"Chainlink": 100.5, "Uniswap": 100.7}
    assert detector.check_for_manipulation(safe_prices, current_timestamp=200) is False
    assert circuit.state == CircuitBreakerState.CLOSED

    manipulated_prices = {"Chainlink": 100.0, "Uniswap": 110.0}
    assert detector.check_for_manipulation(manipulated_prices, current_timestamp=200) is True
    assert circuit.state == CircuitBreakerState.OPEN


def test_detector_flags_single_source_bias_against_twap():
    circuit = CircuitBreaker("oracle-detector-single-source", failure_threshold=1, recovery_timeout_seconds=10)
    oracle = TWAPOracle(window_size_seconds=300)
    _seed_oracle(oracle, base_price=100.0)
    detector = OracleManipulationDetector(oracle, circuit, deviation_threshold_percentage=5.0)

    # Baseline should pass
    assert detector.check_for_manipulation({"DexA": 101.0}, current_timestamp=400) is False
    assert circuit.state == CircuitBreakerState.CLOSED

    # Single source deviating 12% from TWAP must trip the breaker even without corroborating sources
    assert detector.check_for_manipulation({"DexA": 112.0}, current_timestamp=400) is True
    assert circuit.state == CircuitBreakerState.OPEN


def test_detector_spots_twap_attack_with_consistent_sources():
    circuit = CircuitBreaker("oracle-detector-twap-attack", failure_threshold=1, recovery_timeout_seconds=10)
    oracle = TWAPOracle(window_size_seconds=300)
    _seed_oracle(oracle, base_price=100.0)
    detector = OracleManipulationDetector(oracle, circuit, deviation_threshold_percentage=4.0)

    # Two colluding sources both publish a synchronized spike that exceeds the TWAP bounds.
    colluding_prices = {"Chainlink": 118.0, "Uniswap": 119.0}
    assert detector.check_for_manipulation(colluding_prices, current_timestamp=400) is True
    assert circuit.state == CircuitBreakerState.OPEN


def test_flash_loan_protection_detects_price_impact_and_oracle_issues():
    circuit = CircuitBreaker("flash-loan", failure_threshold=1, recovery_timeout_seconds=10)
    oracle = TWAPOracle(window_size_seconds=300)
    _seed_oracle(oracle, base_price=100.0)
    detector = OracleManipulationDetector(oracle, circuit, deviation_threshold_percentage=5.0)
    manager = FlashLoanProtectionManager(
        oracle,
        detector,
        circuit,
        max_price_impact_percentage=2.0,
    )

    prices = {"Chainlink": 100.5, "Uniswap": 100.4}
    assert manager.check_transaction_for_flash_loan_risk(
        {"type": "swap", "asset": "XAI", "amount": 1_000}, prices, asset_liquidity=1_000_000, current_timestamp=400
    ) is False

    # Large trade should exceed the 2% price impact threshold
    risky = manager.check_transaction_for_flash_loan_risk(
        {"type": "swap", "asset": "XAI", "amount": 200_000},
        prices,
        asset_liquidity=1_000_000,
        current_timestamp=410,
    )
    assert risky is True

    # Manipulated oracle prices also trigger risk
    risky_oracle = manager.check_transaction_for_flash_loan_risk(
        {"type": "borrow", "asset": "XAI", "amount": 1_000},
        {"Chainlink": 150.0, "Uniswap": 100.4},
        asset_liquidity=1_000_000,
        current_timestamp=420,
    )
    assert risky_oracle is True
